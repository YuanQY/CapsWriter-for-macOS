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
        # Given: "你好世界今天天气"已经提交（用三次一致的公开update()调用达到这个
        # 状态；三次一致触发暂停规则，除标点外全部提交，这里没有标点）
        agreement = live_preview.Agreement()
        for _ in range(3):
            agreement.update('你好世界今天天气')
        self.assertEqual(agreement.committed, '你好世界今天天气')
        # When: 接下来三次转写都在"世界"前插入了"啊"，并在"世界"后新增了"很好"
        text = '你好啊世界今天天气很好'
        for _ in range(2):
            agreement.update(text)
        shown = agreement.update(text)
        # Then: 按内容对齐找到"天气"后的尾部，提交"你好世界今天天气很好"而不是位置
        # 对齐导致的重复"气"（这三次转写同样一致，触发暂停规则，全部提交）
        self.assertEqual(agreement.committed, '你好世界今天天气很好')
        self.assertEqual(shown[len(agreement.committed):], '')

    def test_pause_commits_the_tail(self):
        # Given/When: 连续三次一致的转写，且以句号收尾（说话人已经停顿）
        agreement = live_preview.Agreement()
        for _ in range(3):
            shown = agreement.update('我要把代码推送到远程仓库。')
        # Then: 除末尾标点外全部提交，暂定文本为空（holdback 不适用）
        self.assertEqual(agreement.committed, '我要把代码推送到远程仓库')
        self.assertEqual(shown[len(agreement.committed):], '')

    def test_pause_hold_survives_repeated_silent_passes(self):
        # Given: 连续三次一致的转写（带句号）先触发一次暂停提交，尾巴只剩
        # 这一个句号（同 test_pause_commits_the_tail）
        agreement = live_preview.Agreement()
        for _ in range(3):
            agreement.update('我要把代码推送到远程仓库。')
        committed = agreement.committed
        self.assertEqual(committed, '我要把代码推送到远程仓库')
        # When: 说话人保持沉默，同一段话（仍带句号）被反复喂入几次；未提交
        # 尾巴此时只剩这一个句号
        for _ in range(3):
            shown = agreement.update('我要把代码推送到远程仓库。')
        # Then: 不应抛异常，已提交文本保持不变，暂定文本仍为空
        self.assertEqual(agreement.committed, committed)
        self.assertEqual(shown[len(agreement.committed):], '')

        # Given: 换一段没有标点收尾的文本，连续三次一致同样触发暂停提交，
        # 尾巴被清空为空字符串
        agreement2 = live_preview.Agreement()
        text = '今天下午三点开会讨论方案'
        for _ in range(3):
            agreement2.update(text)
        committed2 = agreement2.committed
        self.assertEqual(committed2, text)
        # When: 继续反复喂入同一段文本，未提交尾巴此时是空的（不是标点）
        for _ in range(3):
            shown2 = agreement2.update(text)
        # Then: 同样不应抛异常，已提交文本不变，暂定文本仍为空
        self.assertEqual(agreement2.committed, committed2)
        self.assertEqual(shown2[len(agreement2.committed):], '')

    def test_numeral_at_a_pause_still_waits(self):
        # Given/When: 连续三次一致的转写，末尾是一个未闭合的数字串
        agreement = live_preview.Agreement()
        for _ in range(3):
            shown = agreement.update('价格是一万五千')
        # Then: 数字串整体持有规则仍然生效，暂停也不会把半截数字提前提交
        self.assertEqual(agreement.committed, '价格是')
        self.assertEqual(shown[len(agreement.committed):], '一万五千')

    def test_speech_after_a_pause_loses_nothing(self):
        # Given: 先触发一次暂停提交（同上一场景）
        agreement = live_preview.Agreement()
        for _ in range(3):
            agreement.update('我要把代码推送到远程仓库。')
        self.assertEqual(agreement.committed, '我要把代码推送到远程仓库')
        # When: 说话人继续说话，后续三次转写逐步增加"然后"及其后的内容
        for text in ('我要把代码推送到远程仓库然后',
                     '我要把代码推送到远程仓库然后再说',
                     '我要把代码推送到远程仓库，然后再说一下'):
            shown = agreement.update(text)
            # Then: 每次展示的文本都包含这次转写里的"然后"，没有单元被漏掉
            self.assertIn('然后', shown)

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
        # When: 第三次转写依然一致（三次一致触发暂停规则，holdback 不适用）
        agreement.update(text)
        # Then: 除末尾标点外的全部单元都被提交（这里没有标点）
        self.assertEqual(agreement.committed, '今天下午三点开会讨论方案')

    def test_pause_needs_three_consecutive_agreeing_passes(self):
        # Given: 第一次转写比后面多出结尾两个字（"细节"），第二、三次转写
        # 一致且都是第一次的真前缀
        agreement = live_preview.Agreement()
        longer = '我们下周三上午十点开会讨论方案细节'
        text = '我们下周三上午十点开会讨论方案'
        agreement.update(longer)
        agreement.update(text)
        # When: 第三次转写与第二次一致（连续三次里只有最近两次一致，第一次不算）
        shown = agreement.update(text)
        # Then: 只有两次一致还不够触发暂停规则，holdback 仍然生效，不应把
        # 整条尾巴提交掉，暂定文本不应为空
        self.assertNotEqual(agreement.committed, text, '只有两次一致时不应整体提交')
        self.assertNotEqual(shown[len(agreement.committed):], '',
                             'holdback 仍应生效：两次一致还不够触发暂停规则')
        # When: 第三次一致的转写到达（连续三次都是同一段文本）
        shown = agreement.update(text)
        # Then: 现在真正连续三次一致，触发暂停规则，剩余内容整体提交
        self.assertEqual(agreement.committed, text)
        self.assertEqual(shown[len(agreement.committed):], '')


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
