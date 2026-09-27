# coding: utf-8
"""端到端回归：真实 ws_recv/ws_send + 真实 WorkHandler.loop + 真实 qwen_asr_mlx 引擎。

只在本机已经准备好本地 8bit 模型目录时运行；否则整份跳过并给出明确提示。音频来自
`say -v Eddy`（zh_CN）合成到临时目录，从不使用用户录音。断言的是边界（至少多少条
预览、多快出现第一条预览、有没有出现在日志/标准输出里），不是精确计数，因为一遍
的耗时会受机器上其它 GPU 占用影响。
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import functools
import io
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 必须在导入任何触发模型/仓库解析的模块之前设置，防止联网拉取或回退到 hub id。
os.environ.setdefault('HF_HUB_OFFLINE', '1')

import websockets

from config_server import ModelPaths
from core.protocol import AudioMessage, RecognitionMessage
from core.server.connection.ws_recv import ws_recv
from core.server.connection.ws_send import ws_send
from core.server.engines.factory import EngineFactory
from core.server.state import ServerState, WorkerState
from core.server.worker.work_handler import WorkHandler

SR = 16000
PACKET_FRAMES = 320  # 20ms @ 16kHz，与客户端真实分包大小一致

_MODEL_DIR = ModelPaths.qwen3_asr_mlx_8bit_dir
# 目录本身在仓库里是被跟踪的占位符（只有 .gitkeep），必须确认真正的权重文件存在，
# 否则 resolve_qwen3_asr_mlx_model() 会把这个空目录当成"本地可用"，进而让
# mlx_qwen3_asr 把它当 HuggingFace repo id 处理并尝试联网下载。
_MODEL_READY = sys.platform == 'darwin' and (_MODEL_DIR / 'weights.safetensors').exists()
_SAY_AVAILABLE = shutil.which('say') is not None


def _synthesize(text: str, out_dir: Path, name: str) -> np.ndarray:
    """用系统 say -v Eddy（zh_CN）把文本合成为 16kHz 单声道 float32 数组。

    Eddy 语音包在个别机器上可能未完整下载，此时 say 会静默生成一份几乎无声的音频；
    这里用一个宽松的最短时长检查兜底，不满足就明确跳过而不是产生一个没有真实语音的
    伪测试。
    """
    wav_path = out_dir / f'{name}.wav'
    subprocess.run(
        ['say', '-v', 'Eddy', '-o', str(wav_path), '--data-format=LEI16@16000', text],
        check=True, capture_output=True,
    )
    with wave.open(str(wav_path), 'rb') as f:
        assert f.getframerate() == SR and f.getnchannels() == 1
        pcm = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
    audio = (pcm.astype(np.float32) / 32768.0)
    duration = len(audio) / SR
    # 中文正常语速下限按每秒6.7个汉字估算（已经比自然语速快很多，留足容错）；
    # 明显更短说明这句话没有被完整念出来（常见于语音包未完整下载时的静默失败）。
    han_count = sum('一' <= c <= '鿿' for c in text)
    min_expected = 0.15 * han_count
    if duration < min_expected:
        raise unittest.SkipTest(
            f"say -v Eddy 合成的语音只有 {duration:.3f}s（文本含{han_count}个汉字，"
            f"至少应有{min_expected:.1f}s），疑似该机器上 Eddy 的中文语音包未完整下载，"
            "跳过端到端用例"
        )
    return audio


class ServerHarness:
    """在后台线程里跑一个真实的 websockets server（ws_recv/ws_send）和一个真实的
    WorkHandler.loop()，全部用真实的 ServerState / WorkerState，只是队列换成线程安全
    的 queue.Queue，sockets_id 换成普通 list（同进程多线程不需要跨进程 Manager）。
    """
    def __init__(self, recognizer):
        self.state = ServerState(sockets_id=[], queue_in=queue.Queue(), queue_out=queue.Queue())
        self.app = SimpleNamespace(state=self.state)
        self.worker_state = WorkerState()
        self.handler = WorkHandler(self.state.queue_in, self.state.queue_out,
                                    self.state.sockets_id, self.worker_state)
        # aligner/punc 插件与实时预览无关，跳过加载以保持这份 harness 尽量小。
        self.handler.set_engine(recognizer=recognizer, punc_model=None, aligner=None)
        self.port = None
        self._server = None
        self._ready = threading.Event()
        self._server_thread = None
        self._worker_thread = None

    def start(self):
        self._server_thread = threading.Thread(target=self._run_server_loop, daemon=True)
        self._server_thread.start()
        if not self._ready.wait(timeout=30):
            raise RuntimeError('WebSocket 测试服务未能在 30s 内启动')
        self._worker_thread = threading.Thread(target=self.handler.loop, daemon=True)
        self._worker_thread.start()

    def _run_server_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._serve())

    async def _serve(self):
        handler = functools.partial(ws_recv, app=self.app)
        async with websockets.serve(handler, '127.0.0.1', 0, max_size=None) as server:
            self._server = server
            self.port = server.sockets[0].getsockname()[1]
            self._ready.set()
            await ws_send(self.app)

    def stop(self):
        self.state.queue_in.put(None)
        if self._worker_thread:
            self._worker_thread.join(timeout=10)
        self.state.queue_out.put(None)
        if self._server_thread:
            self._server_thread.join(timeout=10)

    @property
    def uri(self):
        return f'ws://127.0.0.1:{self.port}'


async def _record(uri, samples, task_id, live, timeout, context='', language='auto'):
    """像客户端一样，把samples按20ms真实节奏发送，同时收集服务端返回的每条消息。"""
    messages = []
    time_start = time.time()

    async with websockets.connect(uri, max_size=None) as ws:
        async def sender():
            n = len(samples)
            if n == 0:
                await ws.send(AudioMessage(
                    task_id=task_id, source='mic', data='', is_final=True,
                    time_start=time_start, context=context, language=language, live=live,
                ).to_json())
                return
            for i in range(0, n, PACKET_FRAMES):
                chunk = samples[i:i + PACKET_FRAMES]
                is_final = (i + PACKET_FRAMES) >= n
                msg = AudioMessage(
                    task_id=task_id, source='mic',
                    data=base64.b64encode(chunk.astype(np.float32).tobytes()).decode('ascii'),
                    is_final=is_final, time_start=time_start,
                    context=context, language=language, live=live,
                )
                await ws.send(msg.to_json())
                if not is_final:
                    await asyncio.sleep(PACKET_FRAMES / SR)

        async def receiver():
            while True:
                raw = await ws.recv()
                msg = RecognitionMessage.from_dict(json.loads(raw))
                messages.append(msg)
                if msg.is_final:
                    return

        await asyncio.wait_for(asyncio.gather(sender(), receiver()), timeout=timeout)
    return messages


@unittest.skipUnless(_MODEL_READY, f'本地 qwen_asr_mlx 8bit 模型目录不存在: {_MODEL_DIR}')
@unittest.skipUnless(_SAY_AVAILABLE, '本机没有 say 命令，无法合成测试语音')
class LiveE2ETests(unittest.TestCase):
    """真实模型只加载一次，供本文件全部用例共用。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = tempfile.mkdtemp(prefix='capswriter_live_e2e_')
        cls.recognizer = EngineFactory.create_asr_engine('qwen_asr_mlx')
        cls.harness = ServerHarness(cls.recognizer)
        cls.harness.start()
        cls._next_id = 0

    @classmethod
    def tearDownClass(cls):
        cls.harness.stop()
        if hasattr(cls.recognizer, 'cleanup'):
            cls.recognizer.cleanup()
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)

    def next_task_id(self, label):
        type(self)._next_id += 1
        return f'e2e-{label}-{self._next_id}'

    def synth(self, text, name):
        return _synthesize(text, Path(self._tmp_dir), name)

    def test_hold_run_sends_no_preview(self):
        # Given: hold 模式（live=False）的一段真实语音
        audio = self.synth('我刚用Cloud Code把这个脚本重构了一下，效果很不错', 'hold_basic')
        task_id = self.next_task_id('hold')
        # When: 通过真实的 ws_recv/WorkHandler/引擎完整跑一遍录音
        messages = asyncio.run(_record(self.harness.uri, audio, task_id, live=False,
                                        timeout=len(audio) / SR + 20))
        # Then: 全程没有任何预览消息，只有一条 final，且识别出了非空文本
        previews = [m for m in messages if m.preview]
        finals = [m for m in messages if m.is_final]
        self.assertEqual(previews, [], 'hold 模式不应该收到任何预览消息')
        self.assertEqual(len(finals), 1)
        self.assertTrue(finals[0].text.strip(), 'final 文本不应为空')

    def test_live_run_streams_previews(self):
        # Given: live 模式（live=True）的一段几秒钟的真实语音
        audio = self.synth('价格是一万五千块钱左右，我们再商量一下细节，今天先到这里', 'live_basic')
        task_id = self.next_task_id('live')

        # When: 在捕获 server logger（DEBUG）与标准输出的同时，完整跑一遍实时录音
        stdout_buf = io.StringIO()
        with self.assertLogs('server', level='DEBUG') as log_cm, \
                contextlib.redirect_stdout(stdout_buf):
            messages = asyncio.run(_record(self.harness.uri, audio, task_id, live=True,
                                            timeout=len(audio) / SR + 20))

        previews = [m for m in messages if m.preview]
        finals = [m for m in messages if m.is_final]

        # Then: final 之前至少收到两条预览，且最终确实收到唯一一条 final
        self.assertGreaterEqual(len(previews), 2, '几秒钟的live录音至少应产生两次预览')
        self.assertEqual(len(finals), 1)
        self.assertFalse(any(m.preview for m in finals))

        # Then: 第一条预览本身就应该带有实际识别内容（边界断言，不测精确到2秒的时延）
        self.assertTrue(previews[0].text or previews[0].text_tentative,
                        '第一条预览不应该是空文本')

        # Then: 每一条预览的已提交文本都是上一条的延伸（B6：提交内容只增不改）
        committed_texts = [m.text for m in previews]
        for prev_text, cur_text in zip(committed_texts, committed_texts[1:]):
            self.assertTrue(cur_text.startswith(prev_text),
                            f'已提交文本必须只增不改: {prev_text!r} -> {cur_text!r}')

        # Then: 预览文本不得出现在server日志或标准输出里
        preview_fragments = {m.text for m in previews if len(m.text) >= 4}
        preview_fragments |= {m.text_tentative for m in previews if len(m.text_tentative) >= 4}
        stdout_text = stdout_buf.getvalue()
        for fragment in preview_fragments:
            for line in log_cm.output:
                self.assertNotIn(fragment, line, '预览文本不得写入server日志')
            self.assertNotIn(fragment, stdout_text, '预览文本不得打印到标准输出')

    def test_live_final_matches_hold(self):
        # Given: 同一段真实语音
        audio = self.synth('今天下午三点开会讨论方案，大家提前准备一下材料', 'match_hold')
        # When: 分别以 hold 与 live 模式各跑一遍
        hold_id = self.next_task_id('match-hold')
        live_id = self.next_task_id('match-live')
        hold_messages = asyncio.run(_record(self.harness.uri, audio, hold_id, live=False,
                                             timeout=len(audio) / SR + 20))
        live_messages = asyncio.run(_record(self.harness.uri, audio, live_id, live=True,
                                             timeout=len(audio) / SR + 20))
        hold_final = next(m for m in hold_messages if m.is_final)
        live_final = next(m for m in live_messages if m.is_final)
        # Then: live 模式最终吐出的文本与 hold 模式完全一致（同一条最终识别路径）
        self.assertEqual(live_final.text, hold_final.text)
        # Then: live 模式的 final 之前没有任何消息带着 final 之后才该有的属性冲突
        self.assertFalse(live_final.preview)

    def test_long_live_run_keeps_up(self):
        # Given: 一段约30秒的真实语音（跨越 WINDOW=15s 与 FORCE=25s 两个阈值）
        long_text = (
            '我们今天来聊一聊这个项目最近的进展，首先是服务端这边的实时预览功能，'
            '已经基本联调通过了，识别效果也符合预期，然后是客户端这边的悬浮面板，'
            '还需要再打磨一下交互细节，最后是整体的性能表现，在长时间说话的场景下'
            '也基本能跟得上，没有出现明显的卡顿或者延迟越来越大的情况'
        )
        audio = self.synth(long_text, 'long_run')
        self.assertGreaterEqual(len(audio) / SR, 20.0, '这条语料应当合成出至少20秒的语音')
        task_id = self.next_task_id('long')
        # When: 完整跑一遍这段较长的实时录音
        messages = asyncio.run(_record(self.harness.uri, audio, task_id, live=True,
                                        timeout=len(audio) / SR + 30))
        previews = [m for m in messages if m.preview]
        finals = [m for m in messages if m.is_final]
        duration_s = len(audio) / SR
        # Then: 预览数量与时长大致成比例（每秒约一次，容忍机器繁忙时变慢）
        self.assertGreaterEqual(len(previews), int(duration_s / 3),
                                '长录音里预览不应该早早停止更新')
        self.assertEqual(len(finals), 1)
        self.assertTrue(finals[0].text.strip())
        # Then: 已提交文本全程只增不改
        committed_texts = [m.text for m in previews]
        for prev_text, cur_text in zip(committed_texts, committed_texts[1:]):
            self.assertTrue(cur_text.startswith(prev_text))


if __name__ == '__main__':
    unittest.main()
