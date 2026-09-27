# coding: utf-8
"""
实时预览的提交规则

从 ~/code/open-source/capswriter-ab/stream_eval/run_eval.py 移植过来的
M3-1.0-a3 路径：LocalAgreement-3 + holdback + 数字串整体持有 + 内容对齐，
每次 pass 都重新识别从录音开始到当前的全部音频。评测脚本里的其它策略变体
（M2、keep、forced_align 等）都是被否决的实验分支。原来这里还移植过
a3-w15 的长句冻结窗口（分段超过15秒起找停顿冻结、超过25秒强制冻结），
但在真实一分钟录音上，强制冻结用一次错误的重新识别结果替换掉了已经正确
提交的文本（"一聊"被替换成"医疗"）；不做窗口、每次都对全部音频重新识别，
在用户自己的录音上和 a3-w15 给出的结果一致，所以窗口规则被整体删掉，只
保留这条最简单的规则。

只依赖 numpy / re / difflib，不引入模型，因此可以在不加载 MLX 的情况下做
纯单元测试。
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Callable

import numpy as np

SR = 16000          # 采样率：每秒样本数
INTERVAL = 1.0      # 每隔多少秒新音频跑一次 pass
AGREE = 3           # 连续几次 pass 一致才提交
HOLDBACK = 4        # 每次 pass 末尾保留几个 unit 不提交（末尾的识别最不可靠）

# 一个显示单元：一个中日韩字符，或一个拉丁/数字单词，或一个标点（含其后的空白）。
_UNIT = re.compile(r"(?:[㐀-䶿一-鿿]|[A-Za-z0-9']+|[^\sA-Za-z0-9'㐀-䶿一-鿿])\s*")
_NUMERAL = set("零〇一二三四五六七八九十百千万亿两点0123456789")


def ukey(u: str) -> str:
    """比较用的 key：忽略大小写；所有标点都视为相同，统一记作 "P"。"""
    u = u.strip()
    # \w 在 Python 3 里本就匹配中日韩字符，不需要再并上 㐀-鿿。
    return u.casefold() if re.match(r"\w", u) else "P"


def is_numeral(u: str) -> bool:
    """一个 unit 是否全部由数字/数字相关汉字组成（用于数字串整体持有判断）。"""
    s = u.strip()
    return s and all(c in _NUMERAL for c in s)


def _join(a: str, b: str) -> str:
    """拼接两段文本；如果 a 结尾和 b 开头都是拉丁字母/数字，中间补一个空格，
    避免前一个 pass 里紧跟标点（没有自带空格）的单词和后一个 pass 里新提交的
    单词粘连。移植自 capswriter-ab/stream_eval/run_eval.py 的 join()。"""
    if a and b and re.match(r'[A-Za-z0-9]', a[-1]) and re.match(r'[A-Za-z0-9]', b[0]):
        return a + ' ' + b
    return a + b


class Agreement:
    """LocalAgreement-3 + holdback + 数字串整体持有 + 内容对齐（M3-a3 变体，无开关）。

    一个 unit 要连续 AGREE 次 pass 都一致、且不落在其中任何一次 pass 末尾的
    HOLDBACK 个 unit 之内（音频末尾的识别最不可靠），才会被提交。每次 pass
    都通过内容对齐（difflib）而不是位置去定位"已提交部分之后"的尾巴，这样中间
    插入一个词也不会让已提交文本被误判重复。数字串（如"一万九千"）会一直原样
    悬空在暂定文本里，直到后面跟着一个满足上面两个条件、可以被提交的非数字
    unit，数字串才和它一起整体提交，避免把读到一半的数字提前钉死。
    """

    def __init__(self):
        self.committed = ''
        self.keys: list[str] = []
        self._history: list[list[str]] = []

    def update(self, text: str) -> str:
        """喂入一次 pass 的完整文本，返回"已提交 + 暂定尾巴"（暂定尾巴不含末尾标点）。"""
        cur = _UNIT.findall(text.strip())
        cur_keys = [ukey(u) for u in cur]
        # 定位"已提交部分之后"的起点：位置对得上直接用位置，对不上（前面插入/
        # 删除了内容）就用 difflib 按内容对齐最后一段匹配。
        n = len(self.keys)
        start = n
        if cur_keys[:n] != self.keys:
            blocks = [b for b in SequenceMatcher(None, self.keys, cur_keys, autojunk=False)
                      .get_matching_blocks() if b.size]
            if blocks:
                last = blocks[-1]
                start = min(len(cur_keys), last.b + last.size + (n - last.a - last.size))
        tail, tail_keys = cur[start:], cur_keys[start:]
        tails = self._history[-(AGREE - 1):] + [tail_keys]
        if len(tails) == AGREE:
            limit = min(len(t) for t in tails) - HOLDBACK
            m = 0
            while m < limit and all(t[m] == tail_keys[m] for t in tails):
                m += 1
            # 数字串还没被后面一个（同样可提交的）非数字 unit 关闭之前，回退到
            # 数字串开头，不提交半截数字。
            while m > 0 and is_numeral(tail[m - 1]) and (m >= limit or is_numeral(tail[m])):
                m -= 1
            if m:
                self.committed = _join(self.committed, ''.join(tail[:m]))
                self.keys += tail_keys[:m]
                tail, tail_keys = tail[m:], tail_keys[m:]
                self._history = [t[m:] for t in self._history]
        self._history = (self._history + [tail_keys])[-AGREE:]
        tentative = list(tail)
        while tentative and ukey(tentative[-1]) == 'P':  # 暂定文本不以标点收尾
            tentative.pop()
        return _join(self.committed, ''.join(tentative))


class LiveTask:
    """一次实时录音的增量状态：pipeline 自己持有的音频副本和提交规则状态。
    与 Runner 内部为真正 task_id 维护的缓冲互不影响。"""

    def __init__(self, work):
        self.work = work                  # 该 task_id 第一个 live Work，取 socket/context/language 等元信息用
        self.passes = 0
        self._chunks: list[np.ndarray] = []
        self._total_samples = 0
        self.agreement = Agreement()
        self.next_due = INTERVAL * SR      # 累计音频达到这个采样数时该跑下一次 pass

    def feed(self, samples: np.ndarray) -> None:
        """追加一块新到的音频（float32）。"""
        self._chunks.append(samples)
        self._total_samples += len(samples)

    def due(self) -> bool:
        """是否已经比上次 pass 的触发点多攒了至少 INTERVAL 秒的新音频。"""
        return self._total_samples >= self.next_due

    def step(self, transcribe: Callable[[np.ndarray], str]) -> tuple[str, str]:
        """跑一次 pass：重新识别从录音开始到现在的全部音频，返回 (committed, tentative)。

        transcribe 是"音频 -> 文本"的可调用对象，由调用方接入真实模型（一次性
        任务 id）或测试用的脚本转写函数；这里的规则本身不依赖模型。
        """
        self.passes += 1
        # 先移动 next_due 再调用模型：一次失败/耗时的 pass 也要用掉这次名额，
        # 不能让持续报错的 pass 在每个 20ms 音频包上都重跑一次。
        self.next_due = self._total_samples + INTERVAL * SR

        audio = np.concatenate(self._chunks)
        shown = self.agreement.update(transcribe(audio))
        committed = self.agreement.committed
        return committed, shown[len(committed):]
