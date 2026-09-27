# coding: utf-8
"""live_preview.py 纯规则测试：提交规则（Agreement）与 LiveTask 的整段转写。

只依赖 numpy / re / difflib，不加载模型。按 spec.md 的场景原文断言，用真实的
参考实现（capswriter-ab/stream_eval/run_eval.py 的 Agreement，agree=3、
holdback=4、numeral_hold=True、align=True）逐条核对过期望值。长句冻结窗口已从
设计里去掉（真实模型跑长句时，26 秒处的强制冻结会用错误的 head 转写替换掉正确的
已提交文本），现在每次 pass 都转写目前为止的全部音频，已提交文本只增不改。
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
        # Then: 已提交文本是"我刚用Cloud "（Cloud 后的空格是该单元自带的分隔符，
        # spec.md 里这个场景的原文就带着这个空格）
        self.assertEqual(agreement.committed, '我刚用Cloud ')
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
        # Given: "你好世界"已经提交（用三次一致的公开update()调用达到这个状态，
        # 而不是直接写内部字段）
        agreement = live_preview.Agreement()
        for _ in range(3):
            agreement.update('你好世界今天天气')
        self.assertEqual(agreement.committed, '你好世界')
        # When: 接下来三次转写都在"世界"前插入了"啊"，并在"世界"后新增了"今天天气很好"
        text = '你好啊世界今天天气很好'
        for _ in range(2):
            agreement.update(text)
        shown = agreement.update(text)
        # Then: 按内容对齐找到"世界"后的尾部，提交"你好世界今天"而不是位置对齐导致的重复"界"
        self.assertEqual(agreement.committed, '你好世界今天')
        self.assertEqual(shown[len(agreement.committed):], '天气很好')

    def test_trailing_punctuation_hidden(self):
        # Given/When: 单次转写以句号结尾
        agreement = live_preview.Agreement()
        shown = agreement.update('你好，世界。')
        # Then: 暂定文本隐藏了本次转写自己的结尾标点，句中的逗号则保留
        self.assertEqual(shown, '你好，世界')

    def test_glued_latin_words_across_passes_get_a_space(self):
        # Given: 前三次转写一致，"dessert"后紧跟逗号（两者之间没有空格）；
        # "dessert"不在holdback范围内，被提交，逗号还悬在暂定文本里
        agreement = live_preview.Agreement()
        for text in ('我们聊到了dessert，好吃吗',
                     '我们聊到了dessert，好吃吗还不错',
                     '我们聊到了dessert，好吃吗还不错的样子'):
            agreement.update(text)
        self.assertEqual(agreement.committed, '我们聊到了dessert',
                          '"dessert"应该已提交，且提交时后面没有跟着空格')
        # When: 后面的pass识别结果变了：逗号消失，"dessert"后面直接接了新单词"you"
        shown = agreement.update('我们聊到了dessert you know 好吃吗还不错')
        # Then: 暂定文本里"dessert"和"you"之间补了一个空格，而不是粘连成"dessertyou"
        self.assertIn('dessert you know', shown)
        self.assertNotIn('dessertyou', shown)
        # When: 再喂够几次一致的pass，让"you"也被提交
        agreement.update('我们聊到了dessert you know 好吃吗还不错的样子')
        agreement.update('我们聊到了dessert you know 好吃吗还不错的样子啊')
        # Then: 提交后的文本里"dessert"和"you"之间也有空格，不会粘连，且这个空格
        # 一旦提交就不会再被后面的pass改掉（已提交文本只增不改）
        self.assertIn('dessert you', agreement.committed)
        self.assertNotIn('dessertyou', agreement.committed)

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


class LiveTaskTests(unittest.TestCase):
    """LiveTask.step()：没有冻结窗口后，每次 pass 都转写目前为止的全部音频。"""

    def test_step_transcribes_all_audio_so_far_and_committed_only_grows(self):
        # Given: 一个持续说话的live任务，每次都新增1秒音频
        task = live_preview.LiveTask(make_work())
        transcribe = ScriptedTranscribe([
            '今天下午三点开会',
            '今天下午三点开会讨论',
            '今天下午三点开会讨论方案',
            '今天下午三点开会讨论方案大家',
        ])
        committed_history = []
        for _ in range(4):
            task.feed(np.zeros(live_preview.SR, dtype=np.float32))
            committed, tentative = task.step(transcribe)
            committed_history.append(committed)
        # Then: 每一次pass转写的都是"目前为止收到的全部音频"，样本数与累计喂入量相等
        self.assertEqual(transcribe.calls, [live_preview.SR * n for n in (1, 2, 3, 4)])
        # Then: 已提交文本只会变长、不会被后面的pass改写替换（没有冻结窗口就没有强制替换）
        for prev, cur in zip(committed_history, committed_history[1:]):
            self.assertTrue(cur.startswith(prev),
                            f'已提交文本必须只增不改: {prev!r} -> {cur!r}')
        self.assertTrue(committed_history[-1], '连续四次一致的转写应该已经提交了一些内容')


if __name__ == '__main__':
    unittest.main()
