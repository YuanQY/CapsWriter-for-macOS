# coding: utf-8
"""QwenMLXRunnerPipeline + WorkHandler 的实时预览回归：只替身模型（feed_audio_patch /
cancel_task），管线、work handler 与调度队列均为真实实现。

覆盖 B1、B4、B5、B7、B8、B10、B11、B13；不加载模型、不占用麦克风。
"""
from collections import deque
from pathlib import Path
import queue
import sys
import time
import unittest
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.server.schema import Result, Work
from core.server.state import WorkerState
from core.server.worker.qwen_mlx_runner_pipeline import QwenMLXRunnerPipeline
from core.server.worker.work_handler import WorkHandler

SR = 16000


def make_work(task_id='t1', socket_id='s1', offset=0.0, final=False, live=False,
              samples=None, context='', language='auto'):
    """live_preview 只依赖 Work 的少数字段；音频以 float32 数组喂入，转成 bytes 传输。"""
    if samples is None:
        samples = np.zeros(0, dtype=np.float32)
    return Work(source='mic', data=samples.astype(np.float32).tobytes(), offset=offset,
                overlap=0.0, task_id=task_id, socket_id=socket_id, is_final=final,
                time_start=1000.0, time_submit=time.time(), context=context,
                language=language, samplerate=SR, live=live)


class RunnerResult:
    """脚本化的 Runner 返回对象，只提供管线用到的字段。"""
    def __init__(self, text, duration=0.0, finish_reason='stop', truncated=False):
        self.text = text
        self.duration = duration
        self.finish_reason = finish_reason
        self.truncated = truncated


class ScriptedRecognizer:
    """脚本化的识别引擎替身：只实现管线用到的 feed_audio_patch 与 cancel_task。"""
    def __init__(self):
        self.calls = []
        self._live_responses = deque()
        self._final_responses = {}
        self.cancelled = []

    def queue_live_response(self, text_or_exc):
        """按调用顺序为下一次 '#live' 预览pass 提供返回文本，或注入一个待抛出的异常。"""
        self._live_responses.append(text_or_exc)

    def set_final_response(self, task_id, runner_result):
        """为某个真实 task_id 的 final 调用设置返回结果。"""
        self._final_responses[task_id] = runner_result

    def feed_audio_patch(self, *, task_id, audio, sample_rate, is_final, context, language, source):
        self.calls.append(SimpleNamespace(task_id=task_id, samples=len(audio), is_final=is_final))
        # 真实 Runner 对任何 task_id（包括预览pass用的 #live 后缀）都是这样：
        # is_final=False 只缓冲、返回 None；只有 is_final=True 才真正给出结果。
        if not is_final:
            return None
        if '#live' in task_id:
            resp = self._live_responses.popleft()
            if isinstance(resp, BaseException):
                raise resp
            return SimpleNamespace(text=resp)
        return self._final_responses[task_id]

    def cancel_task(self, task_id):
        self.cancelled.append(task_id)


class NoLiveTickPipeline:
    """站在其它引擎（如 WorkPipeline）位置的替身：真实的那些管线只有 process()，
    没有 live_tick，B1的"另一个引擎不发预览"规则要靠 hasattr 分支来保证。"""
    def __init__(self):
        self.calls = []

    def process(self, work):
        self.calls.append(work)
        if not work.is_final:
            return None
        return Result(task_id=work.task_id, socket_id=work.socket_id, source=work.source,
                      is_final=True, text='你好世界')


def live_call_count(recognizer):
    """已经发生过的'#live'预览pass调用次数（在popleft之前记录，因此未脚本化的调用
    也会被计入）：用来证明"没有再跑一次pass"，而不是被吞掉的异常巧合返回了None。"""
    return sum('#live' in c.task_id for c in recognizer.calls)


class ScriptedQueue:
    """按脚本顺序驱动 get()/get_nowait()：('value', work) 交付一个包，('empty',) 表示暂无
    数据，('exit',) 交付退出信号。用于精确控制"预览pass"与"final包"到达的先后顺序。"""
    def __init__(self, script):
        self._script = list(script)
        self._pos = 0

    def _next(self):
        kind, *rest = self._script[self._pos]
        self._pos += 1
        if kind == 'empty':
            raise queue.Empty
        if kind == 'exit':
            return None
        return rest[0]

    def get(self, block=True, timeout=None):
        return self._next()

    def get_nowait(self):
        return self._next()


class PipelineLiveTests(unittest.TestCase):
    """B1/B4/B5/B7/B11/B13：直接对 QwenMLXRunnerPipeline 调 process()/live_tick()。"""

    def make_pipeline(self, recognizer):
        return QwenMLXRunnerPipeline(recognizer, state=WorkerState())

    def test_hold_task_never_runs_a_pass(self):
        # Given: hold 模式（live=False）的非 final 工作单元
        recognizer = ScriptedRecognizer()
        pipeline = self.make_pipeline(recognizer)
        work = make_work(live=False, samples=np.zeros(SR, dtype=np.float32))
        # When: 处理该工作单元后尝试触发一次 live_tick
        result = pipeline.process(work)
        tick = pipeline.live_tick()
        # Then: 不产生预览结果，也不会为该任务创建 LiveTask，且从未尝试过一次预览pass调用
        self.assertIsNone(result)
        self.assertIsNone(tick)
        self.assertEqual(pipeline.live, {})
        self.assertEqual(live_call_count(recognizer), 0)

    def test_pass_cadence_follows_audio_time(self):
        # Given: 一个live任务，每次process()喂入不足1秒的音频
        recognizer = ScriptedRecognizer()
        pipeline = self.make_pipeline(recognizer)
        half_second = np.zeros(SR // 2, dtype=np.float32)
        pipeline.process(make_work(live=True, samples=half_second))
        # Then: 累计音频不足1秒，不产生预览，也没有尝试过一次调用（不是靠异常吞掉
        # 伪装出来的None：调用次数在popleft之前就会被记录）
        self.assertIsNone(pipeline.live_tick())
        self.assertEqual(live_call_count(recognizer), 0)
        # When: 再喂入音频，累计恰好达到1秒
        recognizer.queue_live_response('你好')
        pipeline.process(make_work(live=True, samples=half_second))
        result = pipeline.live_tick()
        # Then: 第一次pass在恰好1秒时触发
        self.assertIsNotNone(result)
        self.assertEqual(pipeline.live['t1'].passes, 1)
        self.assertEqual(live_call_count(recognizer), 1)
        # When: 立刻再次tick，期间没有新增音频
        # Then: 不会额外运行第二次pass
        self.assertIsNone(pipeline.live_tick())
        self.assertEqual(live_call_count(recognizer), 1)
        # When: 再喂入不足1秒的音频
        pipeline.process(make_work(live=True, samples=np.zeros(SR // 4, dtype=np.float32)))
        # Then: 仍未凑够下一秒，不产生预览，调用次数也没有增加
        self.assertIsNone(pipeline.live_tick())
        self.assertEqual(live_call_count(recognizer), 1)

    def test_preview_result_fields(self):
        # Given: 一个恰好积累1秒音频的live任务
        recognizer = ScriptedRecognizer()
        pipeline = self.make_pipeline(recognizer)
        work = make_work(task_id='t1', socket_id='s9', live=True,
                          samples=np.zeros(SR, dtype=np.float32))
        pipeline.process(work)
        recognizer.queue_live_response('你好世界')
        # When: 触发一次预览pass
        result = pipeline.live_tick()
        # Then: 预览 Result 的字段符合约定（没有消费者读取预览的时间戳/时长字段，
        # 这里只断言客户端实际会用到的部分）
        self.assertEqual(result.task_id, 't1')
        self.assertEqual(result.socket_id, 's9')
        self.assertEqual(result.source, 'mic')
        self.assertTrue(result.preview)
        self.assertFalse(result.is_final)
        self.assertIsInstance(result.text, str)
        self.assertIsInstance(result.text_tentative, str)

    def test_final_pops_live_task(self):
        # Given: 一个已经创建了LiveTask的live任务
        recognizer = ScriptedRecognizer()
        pipeline = self.make_pipeline(recognizer)
        pipeline.process(make_work(live=True, samples=np.zeros(SR, dtype=np.float32)))
        self.assertIn('t1', pipeline.live)
        recognizer.set_final_response('t1', RunnerResult(text='你好世界', duration=1.0))
        # When: final包到达
        result = pipeline.process(make_work(live=True, final=True))
        # Then: final结果照常返回，且该任务的LiveTask已被弹出，之后再tick也拿不到它
        self.assertTrue(result.is_final)
        self.assertEqual(result.text, '你好世界')
        self.assertNotIn('t1', pipeline.live)
        self.assertIsNone(pipeline.live_tick())
        self.assertEqual(live_call_count(recognizer), 0, '弹出后不应再尝试任何预览pass调用')

    def test_failing_pass_does_not_break_final(self):
        # Given: 预览pass的模型调用会抛出异常
        recognizer = ScriptedRecognizer()
        recognizer.queue_live_response(RuntimeError('boom'))
        recognizer.set_final_response('t1', RunnerResult(text='你好世界', duration=1.0))
        pipeline = self.make_pipeline(recognizer)
        pipeline.process(make_work(live=True, samples=np.zeros(SR, dtype=np.float32)))
        # When: 该次pass抛出异常
        with self.assertLogs('server', level='DEBUG') as cm:
            result = pipeline.live_tick()
        # Then: 预览调用返回None，异常被吞掉，且这一秒的预算已经用掉（不会立刻重试）
        self.assertIsNone(result)
        self.assertEqual(pipeline.live['t1'].passes, 1, '失败的pass也要占用一次预算')
        # Then: 异常记录只有task_id前缀和异常类型，不包含任何已提交/暂定/脚本化文本
        error_lines = [line for line in cm.output if line.startswith('ERROR:')]
        self.assertEqual(len(error_lines), 1)
        self.assertIn('t1', error_lines[0])
        self.assertIn('RuntimeError', error_lines[0])
        for leaked in ('你好世界', '你好', 'boom'):
            self.assertNotIn(leaked, error_lines[0], '异常记录不得包含已提交/暂定/脚本化文本')
        calls_after_failure = live_call_count(recognizer)
        # When: 只再喂入不到1秒的新音频就立刻再tick
        pipeline.process(make_work(live=True, samples=np.zeros(SR // 2, dtype=np.float32)))
        self.assertIsNone(pipeline.live_tick())
        # Then: next_due 必须在模型调用之前就已推进；不足1秒新音频不应该再调用一次模型
        self.assertEqual(live_call_count(recognizer), calls_after_failure,
                         '不足1秒新音频时不应该重试失败的pass')
        # When: 再喂入音频，凑够1秒新增量后重试
        recognizer.queue_live_response('你好')
        pipeline.process(make_work(live=True, samples=np.zeros(SR // 2, dtype=np.float32)))
        retried = pipeline.live_tick()
        # Then: 凑够1秒新音频后应该正常再跑一次pass
        self.assertIsNotNone(retried)
        self.assertEqual(live_call_count(recognizer), calls_after_failure + 1)
        # When: final包随后到达
        final_result = pipeline.process(make_work(live=True, final=True))
        # Then: final依旧正常输出，不受失败的预览pass影响
        self.assertTrue(final_result.is_final)
        self.assertEqual(final_result.text, '你好世界')

    def test_empty_preview_produces_no_result(self):
        # Given: 预览pass的转写结果是空字符串（既未提交也没有暂定内容）
        recognizer = ScriptedRecognizer()
        recognizer.queue_live_response('')
        pipeline = self.make_pipeline(recognizer)
        pipeline.process(make_work(live=True, samples=np.zeros(SR, dtype=np.float32)))
        # When: 触发一次预览pass
        result = pipeline.live_tick()
        # Then: 面板只在首个非空文本时才打开，空文本不产生预览Result（这次pass确实
        # 跑过一次，不是被 due() 挡在门外）
        self.assertIsNone(result)
        self.assertEqual(live_call_count(recognizer), 1)

    def test_cleanup_drops_live_task(self):
        # Given: 一个已经创建了LiveTask的live任务
        recognizer = ScriptedRecognizer()
        pipeline = self.make_pipeline(recognizer)
        pipeline.process(make_work(live=True, samples=np.zeros(SR, dtype=np.float32)))
        self.assertIn('t1', pipeline.live)
        # When: 客户端断连触发清理
        pipeline.cleanup_tasks(['t1'])
        # Then: 实时任务被同步释放，识别引擎也收到取消通知，之后的tick找不到它
        self.assertNotIn('t1', pipeline.live)
        self.assertEqual(recognizer.cancelled, ['t1'])
        self.assertIsNone(pipeline.live_tick())
        self.assertEqual(live_call_count(recognizer), 0, '清理后不应再尝试任何预览pass调用')

    def test_preview_is_not_logged(self):
        # Given: 预览文本中包含一个绝不应出现在任何日志记录里的标记
        marker = 'MARKER_不许落盘的预览文本'
        recognizer = ScriptedRecognizer()
        recognizer.queue_live_response(marker)
        pipeline = self.make_pipeline(recognizer)
        work = make_work(live=True, samples=np.zeros(SR, dtype=np.float32))
        # When: 在 DEBUG 级别捕获 server logger 的同时跑完一次预览pass
        with self.assertLogs('server', level='DEBUG') as cm:
            pipeline.process(work)
            result = pipeline.live_tick()
        # Then: 预览文本确实生成了，但没有任何一条日志记录包含它
        self.assertIsNotNone(result)
        self.assertIn(marker, result.text + result.text_tentative)
        for line in cm.output:
            self.assertNotIn(marker, line, '预览文本不得出现在任何日志记录里')


class WorkHandlerLiveTests(unittest.TestCase):
    """B8：用受控队列驱动真实 WorkHandler.loop()，检查final不会排在预览pass之后。"""

    def test_final_is_not_queued_behind_passes(self):
        # Given: 一个live任务先到达1秒音频；对应的final包要等第一次预览pass处理完、
        # WorkHandler再次因buffer为空发起阻塞获取时才"到达"。
        recognizer = ScriptedRecognizer()
        recognizer.queue_live_response('你好')
        recognizer.set_final_response('t1', RunnerResult(text='你好世界', duration=1.0))
        pipeline = QwenMLXRunnerPipeline(recognizer, state=WorkerState())
        live_work = make_work(live=True, samples=np.zeros(SR, dtype=np.float32))
        final_work = make_work(live=True, final=True)
        incoming = ScriptedQueue([
            ('value', live_work), ('empty',), ('value', final_work), ('empty',), ('exit',),
        ])
        handler = WorkHandler(incoming, queue.Queue(), ['s1'], WorkerState())
        handler.pipeline = pipeline
        # When: 运行真实的工作循环
        handler.loop()
        # Then: 恰好收到一次预览结果和一次final结果，且预览在前、final在后
        results = []
        while True:
            try:
                results.append(handler.queue_out.get_nowait())
            except queue.Empty:
                break
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0].preview and not results[0].is_final)
        self.assertTrue(results[1].is_final and not results[1].preview)
        # Then: 预览pass只被真正触发过一次（final到达前后都没有被重复触发）
        self.assertEqual(live_call_count(recognizer), 1)

    def test_live_and_final_drained_together_skips_live_tick(self):
        # Given: live音频包和final包在同一批drain_queue()里一起进入buffer（final包
        # 紧跟其后就到达，而不是等预览pass处理完才到达）
        recognizer = ScriptedRecognizer()
        recognizer.set_final_response('t1', RunnerResult(text='你好世界', duration=1.0))
        pipeline = QwenMLXRunnerPipeline(recognizer, state=WorkerState())
        live_work = make_work(live=True, samples=np.zeros(SR, dtype=np.float32))
        final_work = make_work(live=True, final=True)
        incoming = ScriptedQueue([
            ('value', live_work), ('value', final_work), ('empty',), ('empty',), ('exit',),
        ])
        handler = WorkHandler(incoming, queue.Queue(), ['s1'], WorkerState())
        handler.pipeline = pipeline
        # When: 运行真实的工作循环
        handler.loop()
        # Then: 处理完live包时buffer里已经有final在排队，这一轮不会去跑预览pass；
        # 只有final这一条结果
        self.assertEqual(live_call_count(recognizer), 0)
        results = []
        while True:
            try:
                results.append(handler.queue_out.get_nowait())
            except queue.Empty:
                break
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_final)

    def test_other_engine_pipeline_sends_no_partials(self):
        # Given: 管线站在其它引擎（不是qwen_asr_mlx）的位置，只有process()，没有
        # live_tick——真实的WorkPipeline就是这个形状。live=True的包对它没有特殊意义。
        pipeline = NoLiveTickPipeline()
        live_work = make_work(live=True, samples=np.zeros(SR, dtype=np.float32))
        final_work = make_work(live=True, final=True)
        incoming = ScriptedQueue([
            ('value', live_work), ('empty',), ('value', final_work), ('empty',), ('exit',),
        ])
        handler = WorkHandler(incoming, queue.Queue(), ['s1'], WorkerState())
        handler.pipeline = pipeline
        # When: 运行真实的工作循环（捕获server日志，确认没有因为缺 live_tick 出错）
        with self.assertLogs('server', level='DEBUG') as cm:
            handler.loop()
        # Then: 只有final这一条结果到达queue_out，没有任何预览
        results = []
        while True:
            try:
                results.append(handler.queue_out.get_nowait())
            except queue.Empty:
                break
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_final)
        # Then: 没有任何error级别的记录（hasattr分支不能让缺 live_tick 的管线出错）
        self.assertFalse(any(line.startswith('ERROR:') for line in cm.output),
                         '没有 live_tick 的管线不应该让工作循环报错')

    def test_cleanup_via_work_handler_drops_live_task(self):
        # Given: 一个真实的WorkHandler；live任务和它的session都通过真实process()
        # 创建（不是直接调pipeline.cleanup_tasks），对应socket 's1'
        recognizer = ScriptedRecognizer()
        state = WorkerState()
        pipeline = QwenMLXRunnerPipeline(recognizer, state=state)
        sockets_id = ['s1']
        handler = WorkHandler(queue.Queue(), queue.Queue(), sockets_id, state)
        handler.pipeline = pipeline
        pipeline.process(make_work(socket_id='s1', live=True,
                                    samples=np.zeros(SR, dtype=np.float32)))
        self.assertIn('t1', pipeline.live)
        self.assertIn('t1', state.sessions)
        # When: socket 's1' 断连（从sockets_id移除），触发真实的handler.cleanup()
        sockets_id.remove('s1')
        handler.cleanup()
        # Then: live任务和session都被清理，之后的tick也拿不到预览
        self.assertNotIn('t1', pipeline.live)
        self.assertNotIn('t1', state.sessions)
        self.assertIsNone(pipeline.live_tick())

    def test_empty_preview_reaches_no_queue_out(self):
        # Given: 只有一个live任务，其预览pass的转写结果是空字符串
        recognizer = ScriptedRecognizer()
        recognizer.queue_live_response('')
        pipeline = QwenMLXRunnerPipeline(recognizer, state=WorkerState())
        live_work = make_work(live=True, samples=np.zeros(SR, dtype=np.float32))
        incoming = ScriptedQueue([('value', live_work), ('empty',), ('exit',)])
        handler = WorkHandler(incoming, queue.Queue(), ['s1'], WorkerState())
        handler.pipeline = pipeline
        # When: 运行真实的工作循环
        handler.loop()
        # Then: 空文本的预览不会被放上 queue_out
        with self.assertRaises(queue.Empty):
            handler.queue_out.get_nowait()


if __name__ == '__main__':
    unittest.main()
