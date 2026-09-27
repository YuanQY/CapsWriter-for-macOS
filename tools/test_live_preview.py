# coding: utf-8
"""live_preview.py 纯规则测试：提交规则（Agreement）与长句窗口规则（LiveTask）。

只依赖 numpy / re / difflib，不加载模型。按 spec.md 的场景原文断言，用真实的
参考实现（capswriter-ab/stream_eval/run_eval.py 的 Agreement，agree=3、
holdback=4、numeral_hold=True、align=True）逐条核对过期望值。
"""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.server.worker import live_preview
from core.server.schema import Work


def make_work(task_id='t1', socket_id='s1'):
    """LiveTask 只读取 work 的 task_id/socket_id/source/context/language/time_start。"""
    return Work(source='mic', data=b'', offset=0.0, overlap=0.0, task_id=task_id,
                socket_id=socket_id, is_final=False, time_start=0.0, time_submit=0.0,
                context='', language='auto')


def make_tone(duration_s, quiet_at=None, quiet_dur=1.0):
    """造一段等幅音调；quiet_at 秒起插入 quiet_dur 秒静音，模拟一次真实停顿。"""
    n = int(duration_s * live_preview.SR)
    t = np.arange(n, dtype=np.float32) / live_preview.SR
    audio = (0.5 * np.sin(2 * np.pi * 220.0 * t)).astype(np.float32)
    if quiet_at is not None:
        lo = int(quiet_at * live_preview.SR)
        hi = int((quiet_at + quiet_dur) * live_preview.SR)
        audio[lo:hi] = 0.0
    return audio


class ScriptedTranscribe:
    """按调用顺序返回预设文本，并记录每次调用收到的音频样本数。"""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, audio):
        self.calls.append(len(audio))
        return self.responses[len(self.calls) - 1]


class AgreementTests(unittest.TestCase):
    """提交规则：agree=3、holdback=4、numeral_hold、内容对齐（均为硬编码，无参数）。"""

    def test_tail_word_not_committed_early(self):
        # Given: 连续三次不一致的尾部转写（"我刚用Cloud" -> ... -> 加了"脚本重构"）
        agreement = live_preview.Agreement()
        for text in ('我刚用Cloud', '我刚用cloud code把这个', '我刚用cloud code把这个脚本重构'):
            agreement.update(text)
        # Then: 三次都不足以让任何单元提交
        self.assertEqual(agreement.committed, '', '三次不一致的尾部不应提交任何内容')
        # When: 第四次转写与前三次的公共前缀一致，且不在保留尾部（holdback=4）之内
        shown = agreement.update('我刚用Cloud Code把这个脚本重构了一下')
        # Then: 已提交文本是"我刚用Cloud"（Cloud 后的空格是该单元自带的分隔符）
        self.assertEqual(agreement.committed.rstrip(), '我刚用Cloud')
        self.assertEqual(shown, '我刚用Cloud Code把这个脚本重构了一下')

    def test_open_numeral_run_waits(self):
        # Given: 前两次转写都在数字串"一万五千"处于未闭合状态
        agreement = live_preview.Agreement()
        for text in ('价格是一万五千块钱左右', '价格是一万五千块钱左右吧'):
            agreement.update(text)
        # When: 第三次转写仍然一致
        shown = agreement.update('价格是一万五千块钱左右吧我觉得')
        # Then: 数字串前的"价格是"提交，数字串本身还是暂定文本的开头
        self.assertEqual(agreement.committed, '价格是')
        self.assertTrue(shown[len(agreement.committed):].startswith('一万五千'),
                         '开放的数字串在闭合前不应提交')
        # When: 第四次转写用一个非数字单元闭合了数字串
        agreement.update('价格是一万五千块钱左右吧我觉得可以')
        # Then: 数字串连同其前缀一起提交
        self.assertEqual(agreement.committed, '价格是一万五千块')

    def test_insertion_does_not_duplicate_tail(self):
        # Given: "你好世界"已经提交（模拟此前若干次通过验证的转写）
        agreement = live_preview.Agreement()
        agreement.committed = '你好世界'
        agreement.keys = [live_preview.ukey(u) for u in live_preview.units('你好世界')]
        # When: 接下来三次转写都在"世界"前插入了"啊"，并在"世界"后新增了"今天天气很好"
        text = '你好啊世界今天天气很好'
        for _ in range(2):
            agreement.update(text)
        shown = agreement.update(text)
        # Then: 按内容对齐找到"世界"后的尾部，提交"你好世界今天"而不是位置对齐导致的重复"界"
        self.assertEqual(agreement.committed, '你好世界今天')
        self.assertNotEqual(agreement.committed, '你好世界界今天')
        self.assertEqual(shown[len(agreement.committed):], '天气很好')

    def test_trailing_punctuation_hidden(self):
        # Given/When: 单次转写以句号结尾
        agreement = live_preview.Agreement()
        shown = agreement.update('你好，世界。')
        # Then: 暂定文本隐藏了本次转写自己的结尾标点，句中的逗号则保留
        self.assertEqual(shown, '你好，世界')
        self.assertFalse(shown.endswith('。'))

    def test_commits_on_third_agreeing_pass(self):
        # Given: 同一段文本连续转写两次
        agreement = live_preview.Agreement()
        text = '今天下午三点开会讨论方案'
        agreement.update(text)
        agreement.update(text)
        # Then: 两次一致还不够，agree=3 要求第三次
        self.assertEqual(agreement.committed, '', '只有两次一致时不应提交')
        # When: 第三次转写依然一致
        agreement.update(text)
        # Then: 提交除保留尾部（holdback=4）外的全部单元
        self.assertEqual(agreement.committed, '今天下午三点开会')


class WindowRuleTests(unittest.TestCase):
    """长句窗口规则：LiveTask.step() 里 WINDOW=15s / FORCE=25s 的冻结判断。"""

    def test_freeze_keeps_agreed_committed(self):
        # Given: 已提交"你好"，一段16秒的实时片段在搜索窗口内有一次真实停顿
        task = live_preview.LiveTask(make_work())
        task.agreement.committed = '你好'
        task.agreement.keys = ['你', '好']
        audio = make_tone(16.0, quiet_at=10.0, quiet_dur=1.0)
        task.feed(audio)
        transcribe = ScriptedTranscribe(['你好在吗', '现在几点'])
        # When: 停顿前的转写以已提交单元开头
        committed, tentative = task.step(transcribe)
        # Then: 已提交文本不变，转写余下部分被追加；下一段只覆盖停顿之后的新音频
        self.assertEqual(committed, '你好在吗')
        self.assertEqual(len(transcribe.calls), 2)
        self.assertTrue(10.0 * live_preview.SR <= task.seg_start <= 11.0 * live_preview.SR)
        self.assertEqual(transcribe.calls[1], len(audio) - task.seg_start)

    def test_freeze_waits_when_head_disagrees(self):
        # Given: 已提交"你好"，同样16秒的片段有停顿，但段长未超过FORCE=25s
        task = live_preview.LiveTask(make_work())
        task.agreement.committed = '你好'
        task.agreement.keys = ['你', '好']
        audio = make_tone(16.0, quiet_at=10.0, quiet_dur=1.0)
        task.feed(audio)
        transcribe = ScriptedTranscribe(['不好意思打扰了', '你好我想问一下'])
        # When: 停顿前的转写不以已提交单元开头
        committed, tentative = task.step(transcribe)
        # Then: 不冻结，已提交文本不变，下一段仍覆盖整个未冻结片段
        self.assertEqual(committed, '你好')
        self.assertEqual(task.seg_start, 0)
        self.assertEqual(len(transcribe.calls), 2)
        self.assertEqual(transcribe.calls[1], len(audio))

    def test_forced_freeze_replaces_head(self):
        # Given: 已提交"你好"，一段26秒的片段超过FORCE=25s，搜索窗口内有一次停顿
        task = live_preview.LiveTask(make_work())
        task.agreement.committed = '你好'
        task.agreement.keys = ['你', '好']
        audio = make_tone(26.0, quiet_at=10.0, quiet_dur=1.0)
        task.feed(audio)
        transcribe = ScriptedTranscribe(['今天天气不错我们出去走走吧', '好呀就这么定了'])
        # When: 停顿前的转写不以已提交单元开头，但段长已超过强制阈值
        committed, tentative = task.step(transcribe)
        # Then: 依然在该帧冻结，已提交文本被这段转写整体替换
        self.assertEqual(committed, '今天天气不错我们出去走走吧')
        self.assertTrue(10.0 * live_preview.SR <= task.seg_start <= 11.0 * live_preview.SR)

    def test_pass_audio_is_bounded(self):
        # Given: 与强制冻结相同的26秒片段
        task = live_preview.LiveTask(make_work())
        task.agreement.committed = '你好'
        task.agreement.keys = ['你', '好']
        audio = make_tone(26.0, quiet_at=10.0, quiet_dur=1.0)
        task.feed(audio)
        transcribe = ScriptedTranscribe(['今天天气不错我们出去走走吧', '好呀就这么定了'])
        # When: 触发一次强制冻结
        task.step(transcribe)
        # Then: 冻结后的正式一遍只覆盖冻结点之后的新音频，而不是整段26秒
        main_pass_len = transcribe.calls[1]
        self.assertEqual(main_pass_len, len(audio) - task.seg_start)
        self.assertLess(main_pass_len, len(audio), '一遍的音频量必须有界，不能随录音总长增长')


if __name__ == '__main__':
    unittest.main()
