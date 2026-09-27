# coding: utf-8
"""
实时预览的提交规则与长句冻结窗口

从 ~/code/open-source/capswriter-ab/stream_eval/run_eval.py 移植过来的
M3-1.0-a3-w15 路径：LocalAgreement-3 + holdback + 数字串整体持有 + 内容对齐，
外加"分段超过15秒起找停顿冻结、超过25秒强制冻结"的窗口规则。评测脚本里的
其它策略变体（M2、keep、forced_align 等）都是被否决的实验分支，这里只保留
最终选定的这一条，且去掉了所有开关：agree/holdback/numeral_hold/align 等
在评测里可调的参数，在这里固定为模块常量或硬编码逻辑。

只依赖 numpy / re / difflib，不引入模型，因此可以在不加载 MLX 的情况下做
纯单元测试。
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Callable, Optional

import numpy as np

SR = 16000          # 采样率：每秒样本数
FRAME = 320         # 20ms 一帧
INTERVAL = 1.0      # 每隔多少秒新音频跑一次 pass
AGREE = 3           # 连续几次 pass 一致才提交
HOLDBACK = 4        # 每次 pass 末尾保留几个 unit 不提交（末尾的识别最不可靠）
WINDOW = 15.0       # 分段超过这个时长（秒）开始找停顿
FORCE = 25.0        # 分段超过这个时长（秒）强制冻结，不再等待一致
PAUSE_RATIO = 0.2   # 停顿判定：帧 RMS <= 分段中位数 RMS 的这个比例

# 一个显示单元：一个中日韩字符，或一个拉丁/数字单词，或一个标点（含其后的空白）。
_UNIT = re.compile(r"(?:[㐀-䶿一-鿿]|[A-Za-z0-9']+|[^\sA-Za-z0-9'㐀-䶿一-鿿])\s*")
_NUMERAL = set("零〇一二三四五六七八九十百千万亿两点0123456789")


def units(text: str) -> list[str]:
    """把文本切成显示单元列表。"""
    return _UNIT.findall(text.strip())


def ukey(u: str) -> str:
    """比较用的 key：忽略大小写；所有标点都视为相同，统一记作 "P"。"""
    u = u.strip()
    return u.casefold() if re.match(r"[\w㐀-鿿]", u) else "P"


def is_numeral(u: str) -> bool:
    """一个 unit 是否全部由数字/数字相关汉字组成（用于数字串整体持有判断）。"""
    s = u.strip()
    return bool(s) and all(c in _NUMERAL for c in s)


def join(a: str, b: str) -> str:
    """拼接两段文本；只有在拉丁/数字边界才补一个空格，中文之间不加空格。"""
    if a and b and re.match(r"[A-Za-z0-9]", a[-1]) and re.match(r"[A-Za-z0-9]", b[0]):
        return a + " " + b
    return a + b


def quiet_cut(audio: np.ndarray, lo: int, hi: int) -> int:
    """[lo, hi) 区间内最安静的 20ms 帧的起点采样下标；不足一帧时退化为 hi。"""
    if hi - lo < FRAME:
        return hi
    seg = audio[lo:hi][: (hi - lo) // FRAME * FRAME].reshape(-1, FRAME)
    return lo + int(np.argmin((seg ** 2).mean(axis=1))) * FRAME


def pause_cut(audio: np.ndarray, lo: int, hi: int, seg_lo: int, seg_hi: int) -> Optional[int]:
    """[lo, hi) 里最安静的一帧，只有其 RMS 不超过整段中位数 RMS 的 PAUSE_RATIO 倍
    才算一次真正的停顿；否则返回 None（这一段其实还在说话，不能当停顿冻结）。"""
    if hi - lo < FRAME:
        return None

    def rms(x: np.ndarray) -> np.ndarray:
        return np.sqrt((x[: len(x) // FRAME * FRAME].reshape(-1, FRAME) ** 2).mean(axis=1))

    seg = rms(audio[seg_lo:seg_hi])
    win = rms(audio[lo:hi])
    i = int(np.argmin(win))
    return lo + i * FRAME if win[i] <= PAUSE_RATIO * float(np.median(seg)) else None


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

    def _tail_start(self, cur_keys: list[str]) -> int:
        """在新 pass 里定位"已提交部分之后"的起点：位置对得上直接用位置，
        对不上（前面插入/删除了内容）就用 difflib 按内容对齐最后一段匹配。"""
        n = len(self.keys)
        if cur_keys[:n] == self.keys:
            return n
        blocks = [b for b in SequenceMatcher(None, self.keys, cur_keys, autojunk=False)
                  .get_matching_blocks() if b.size]
        if not blocks:
            return n
        last = blocks[-1]
        return min(len(cur_keys), last.b + last.size + (n - last.a - last.size))

    def update(self, text: str) -> str:
        """喂入一次 pass 的完整文本，返回"已提交 + 暂定尾巴"（暂定尾巴不含末尾标点）。"""
        cur = units(text)
        cur_keys = [ukey(u) for u in cur]
        start = self._tail_start(cur_keys)
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
                self.committed += ''.join(tail[:m])
                self.keys += tail_keys[:m]
                tail, tail_keys = tail[m:], tail_keys[m:]
                self._history = [t[m:] for t in self._history]
        self._history = (self._history + [tail_keys])[-AGREE:]
        tentative = list(tail)
        while tentative and ukey(tentative[-1]) == 'P':  # 暂定文本不以标点收尾
            tentative.pop()
        return self.committed + ''.join(tentative)


class LiveTask:
    """一次实时录音的增量状态：pipeline 自己持有的音频副本、提交规则状态和
    长句冻结窗口状态。与 Runner 内部为真正 task_id 维护的缓冲互不影响。"""

    def __init__(self, work):
        self.work = work                  # 该 task_id 第一个 live Work，取 socket/context/language 等元信息用
        self.passes = 0
        self._chunks: list[np.ndarray] = []
        self._total_samples = 0
        self.seg_start = 0                 # 当前未冻结分段在整段音频里的起点（采样点）
        self.frozen = ''                    # 已冻结、不再由分段规则改写的文本
        self.agreement = Agreement()
        self.next_due = INTERVAL * SR      # 累计音频达到这个采样数时该跑下一次 pass

    @property
    def duration(self) -> float:
        """已收到的音频总时长（秒），供 pipeline 填充 Result.duration。"""
        return self._total_samples / SR

    def feed(self, samples: np.ndarray) -> None:
        """追加一块新到的音频（float32）。"""
        self._chunks.append(samples)
        self._total_samples += len(samples)

    def due(self) -> bool:
        """是否已经比上次 pass 的触发点多攒了至少 INTERVAL 秒的新音频。"""
        return self._total_samples >= self.next_due

    def step(self, transcribe: Callable[[np.ndarray], str]) -> tuple[str, str]:
        """跑一次 pass，返回 (committed, tentative)。

        transcribe 是"音频 -> 文本"的可调用对象，由调用方接入真实模型（一次性
        任务 id）或测试用的脚本转写函数；这里的规则本身不依赖模型。
        """
        self.passes += 1
        # 先移动 next_due 再调用模型：一次失败/耗时的 pass 也要用掉这次名额，
        # 不能让持续报错的 pass 在每个 20ms 音频包上都重跑一次。
        self.next_due = self._total_samples + INTERVAL * SR

        audio = np.concatenate(self._chunks) if len(self._chunks) > 1 else self._chunks[0]
        end = self._total_samples
        seg_start, frozen, agreement = self.seg_start, self.frozen, self.agreement

        # 分段过长时先尝试在中段找一个停顿把分段起点向前冻结，之后的 pass
        # 只需要覆盖冻结点之后的音频，避免越录越长的一次性重新识别。
        if (end - seg_start) / SR > WINDOW:
            lo = seg_start + int(WINDOW * 0.5 * SR)
            hi = end - int(3 * SR)
            force = (end - seg_start) / SR > FORCE
            cut = pause_cut(audio, lo, hi, seg_start, end)
            if cut is None and force:
                cut = quiet_cut(audio, lo, hi)
            if cut is not None:
                head = transcribe(audio[seg_start:cut])
                hu = units(head)
                consistent = [ukey(u) for u in hu[:len(agreement.keys)]] == agreement.keys
                if consistent or force:
                    # 一致：保留用户已经看到的已提交文本，只把 head 里已提交之后
                    # 的部分接上；不一致但被强制冻结：不再信任已提交文本，
                    # 整段换成这次重新识别出来的 head。
                    part = agreement.committed + ''.join(hu[len(agreement.keys):]) if consistent else head
                    frozen = join(frozen, part.strip())
                    seg_start = cut
                    agreement = Agreement()

        text = transcribe(audio[seg_start:end])
        shown = join(frozen, agreement.update(text))
        committed = join(frozen, agreement.committed)

        self.seg_start, self.frozen, self.agreement = seg_start, frozen, agreement
        return committed, shown[len(committed):]
