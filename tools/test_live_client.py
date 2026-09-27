# coding: utf-8 -*-
"""客户端 live 听写模式回归（add-live-dictation-mode，3C 组，只测规格/契约）。

覆盖 B1-B3（录音器按 dictation_mode 给每条 AudioMessage 打 live 标记）、
B10（预览文本绝不可进入任何日志）、B12（客户端预览面板：非激活样式、
提交/暂定文本配色、final 隐藏、AUTO_HIDE 自动隐藏）。

安全边界（对齐 lane-rules.md）：
- 录音器测试只连接本文件自建的本地抓包 WebSocket 服务端（127.0.0.1:0），
  绝不连接生产端口 6016，也绝不启动真实客户端或注册全局快捷键。
- 最终结果分支（B12 的 final 消息）把 ResultProcessor 的输出/粘贴出口整体
  打桩（`_emit_text`），保证不会向用户任何真实 App 粘贴或打字。
- `live_panel` 模块（新文件）在基线提交上不存在：依赖它的用例（B12）允许
  以 ImportError 失败；录音器用例（B1-B3）不依赖该模块，必须以断言失败
  （而不是导入错误）的形式先失败。
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import numpy as np
import websockets

# 保证从任意 cwd 执行时都导入本项目，而不是环境中同名包。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 本回归不触发真实剪贴板/音频设备；测试环境未安装可选依赖时，先提供最小 API
# 让 result_processor/recorder 的导入链能跑通，避免无关依赖遮蔽 live 模式语义断言。
if 'pyclip' not in sys.modules:
    _pyclip_stub = types.ModuleType('pyclip')
    _pyclip_stub.copy = lambda content: None
    _pyclip_stub.paste = lambda: ''
    sys.modules['pyclip'] = _pyclip_stub

if 'sounddevice' not in sys.modules:
    sys.modules['sounddevice'] = types.ModuleType('sounddevice')

from config_client import ClientConfig as Config
from core.client.audio.recorder import AudioRecorder
from core.client.connection import WebSocketManager
from core.client.state import ClientState
from core.protocol import RecognitionMessage

REPO_ROOT = Path(__file__).resolve().parents[1]


def _year_folder_snapshot() -> set:
    """录音年份目录（如 2026/）下现有文件的快照。

    AudioFileManager 用 `Path() / 年 / 月 / 'assets'`（相对 cwd）落盘；测试须以
    仓库根目录启动（lane-contract 约定），故这里直接用 REPO_ROOT 定位同一目录，
    用于证明 save_audio=False 时该目录不会多出任何文件（不碰用户真实录音归档）。
    """
    year_dir = REPO_ROOT / time.strftime('%Y')
    if not year_dir.exists():
        return set()
    return set(year_dir.rglob('*'))


def _pump_main_runloop(seconds: float = 0.05) -> None:
    """把 AppHelper.callAfter/callLater 派发到主线程 RunLoop 的任务挤出来执行。

    仅供 B12 面板用例使用；惰性导入 Foundation，避免影响不需要 AppKit 的用例。
    """
    from Foundation import NSDate, NSRunLoop
    NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(seconds))


class _CaptureServer:
    """只接收、不回复的本地 WebSocket 服务端，用于抓取录音器真实发出的 AudioMessage。"""

    def __init__(self):
        self.received: list = []
        self._server = None

    async def start(self):
        async def _handler(websocket):
            async for raw in websocket:
                self.received.append(json.loads(raw))
        self._server = await websockets.serve(_handler, '127.0.0.1', 0)
        return self._server.sockets[0].getsockname()[:2]

    async def stop(self):
        self._server.close()
        await self._server.wait_closed()


class RecorderLiveModeTests(unittest.IsolatedAsyncioTestCase):
    """B1-B3：真实 AudioRecorder.record_and_send 循环 + 真实 WebSocketManager，
    连接自建的本地抓包服务端（端口 0），验证 dictation_mode 如何决定
    AudioMessage.live 字段。"""

    async def asyncSetUp(self):
        self._orig_addr = Config.addr
        self._orig_port = Config.port
        self._server = _CaptureServer()
        host, port = await self._server.start()
        # 只在测试期间把 Config.addr/port 指向自建抓包服务端；finally 里恢复，
        # 避免影响同进程里其它可能读取 Config 的代码。
        Config.addr = host
        Config.port = str(port)
        self._year_before = _year_folder_snapshot()

    async def asyncTearDown(self):
        Config.addr = self._orig_addr
        Config.port = self._orig_port
        await self._server.stop()

    async def _wait_until(self, predicate, timeout: float = 2.0) -> None:
        """轮询屏障：等到抓包服务端收满预期条数的消息，不用固定 sleep 赌运气。"""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while not predicate() and loop.time() < deadline:
            await asyncio.sleep(0.01)

    async def _connect_recorder(self) -> AudioRecorder:
        """建立一个已连上自建抓包服务端的真实 AudioRecorder，供各录音场景复用。"""
        state = ClientState()
        app = types.SimpleNamespace(state=state, loop=asyncio.get_running_loop())
        app.ws = WebSocketManager(app)
        connected = await app.ws.connect()
        self.assertTrue(connected, '录音测试必须先连上自建抓包服务端')
        return AudioRecorder(app)

    async def _run_recording(self) -> list:
        """驱动一次真实录音：begin -> 两个跨过阈值的 data 分片 -> finish。

        两个 data 分片的时间戳都已超过 Config.threshold（起录阈值），所以各自
        立即触发一次 AudioMessage 发送（recorder.py 的“data”分支），finish 再
        补发一条 is_final=True 的收尾消息，共 3 条，覆盖“每条音频消息”的断言面。
        """
        recorder = await self._connect_recorder()
        block = np.zeros((480, 2), dtype=np.float32)
        recorder.state.queue_in.put_nowait({
            'type': 'begin', 'time': 0.0,
            'trace_id': 'trace-live', 'shortcut_key': 'caps_lock',
        })
        recorder.state.queue_in.put_nowait({
            'type': 'data', 'time': Config.threshold + 0.1, 'data': block,
        })
        recorder.state.queue_in.put_nowait({
            'type': 'data', 'time': Config.threshold + 1.1, 'data': block,
        })
        recorder.state.queue_in.put_nowait({'type': 'finish', 'time': Config.threshold + 1.2})

        await recorder.record_and_send()
        await self._wait_until(lambda: len(self._server.received) >= 3)
        return self._server.received

    async def _run_recording_cache_flushed_at_finish(self) -> list:
        """驱动一次短录音：begin -> 一个未跨阈值的 data 分片（留在 _cache）-> finish。

        recorder.py 的第三处 AudioMessage 构造点在 'finish' 分支里，只有当录音
        结束时仍未跨过 Config.threshold、_cache 还有未发送数据时才会触发；它和
        `_run_recording` 里“跨阈值立即发送”的分支互斥，因此单独用一次短录音覆盖。
        """
        recorder = await self._connect_recorder()
        block = np.zeros((480, 2), dtype=np.float32)
        recorder.state.queue_in.put_nowait({
            'type': 'begin', 'time': 0.0,
            'trace_id': 'trace-live-short', 'shortcut_key': 'caps_lock',
        })
        recorder.state.queue_in.put_nowait({
            'type': 'data', 'time': Config.threshold - 0.1, 'data': block,
        })
        recorder.state.queue_in.put_nowait({'type': 'finish', 'time': Config.threshold - 0.05})

        await recorder.record_and_send()
        await self._wait_until(lambda: len(self._server.received) >= 2)
        return self._server.received

    async def test_recorder_default_sends_hold(self):
        """B1
        Given: dictation_mode 保持默认（未显式设置，即 hold）
        When: 走真实 record_and_send 循环发送一段录音
        Then: 服务端收到的每条 AudioMessage 的 live 字段都是 False
        """
        with patch.object(Config, 'save_audio', False):
            messages = await self._run_recording()

        self.assertGreaterEqual(len(messages), 1, messages)
        self.assertTrue(all(msg.get('live') is False for msg in messages), messages)
        self.assertEqual(_year_folder_snapshot(), self._year_before,
                          'save_audio=False 时不得在年份目录下产生新录音文件')

    async def test_recorder_unknown_mode_sends_hold(self):
        """B2
        Given: dictation_mode 被设为未知取值 'stream'
        When: 走真实 record_and_send 循环发送一段录音
        Then: 未知取值按 hold 处理，所有 AudioMessage 的 live 字段都是 False
        """
        with patch.object(Config, 'save_audio', False), \
                patch.object(Config, 'dictation_mode', 'stream', create=True):
            messages = await self._run_recording()

        self.assertGreaterEqual(len(messages), 1, messages)
        self.assertTrue(all(msg.get('live') is False for msg in messages), messages)
        self.assertEqual(_year_folder_snapshot(), self._year_before)

    async def test_recorder_live_mode_tags_messages(self):
        """B3
        Given: dictation_mode = 'live'
        When: 走真实 record_and_send 循环发送一段录音
        Then: 服务端收到的每一条音频消息都带 live=True
        """
        with patch.object(Config, 'save_audio', False), \
                patch.object(Config, 'dictation_mode', 'live', create=True):
            messages = await self._run_recording()

        self.assertGreaterEqual(len(messages), 1, messages)
        self.assertTrue(all(msg.get('live') is True for msg in messages), messages)
        self.assertEqual(_year_folder_snapshot(), self._year_before)

    async def test_recorder_live_mode_tags_cache_flush_message(self):
        """B3（补充：第三处 AudioMessage 构造点）
        Given: dictation_mode = 'live'，且录音在跨过起录阈值前就结束（数据全部留在缓存）
        When: finish 分支把缓存数据一次性发出
        Then: 该缓存回补消息与收尾消息同样带 live=True
        """
        with patch.object(Config, 'save_audio', False), \
                patch.object(Config, 'dictation_mode', 'live', create=True):
            messages = await self._run_recording_cache_flushed_at_finish()

        self.assertGreaterEqual(len(messages), 2, messages)
        self.assertTrue(all(msg.get('live') is True for msg in messages), messages)
        self.assertEqual(_year_folder_snapshot(), self._year_before)


class ResultProcessorLoggingTests(unittest.IsolatedAsyncioTestCase):
    """B10：预览文本绝不可进入任何日志（服务端的隐私要求同样适用于客户端）。"""

    async def test_preview_is_not_logged(self):
        """B10
        Given: 一条服务端真实产出的预览消息（preview=True，携带已提交与暂定文本），
               经 to_json/from_dict 往返，和真实 ws_send/receive 走的是同一条编解码路径
        When: 交给真实 ResultProcessor._handle_message 处理
        Then: 'client' 日志记录器在 DEBUG 级别下，不出现已提交或暂定文本中的任何一个字
        """
        committed, tentative = '罕见委托文本极光', '暂定尾巴星尘'
        raw = RecognitionMessage(
            task_id='preview-log', is_final=False, duration=1.0, time_start=0.0,
            time_submit=0.5, time_complete=0.6, text=committed,
            preview=True, text_tentative=tentative,
        ).to_json()
        message = RecognitionMessage.from_dict(json.loads(raw))

        from core.client.output.result_processor import ResultProcessor
        app = types.SimpleNamespace(loop=asyncio.get_running_loop())
        processor = ResultProcessor(app)

        # 临时替换 'client' 日志记录器的 handler，只在本用例内收集记录，
        # 不写真实日志文件，也不影响其它测试或真实运行时的日志配置。
        client_logger = logging.getLogger('client')
        captured: list = []

        class _Collector(logging.Handler):
            def emit(self, record):
                captured.append(record)

        collector = _Collector()
        collector.setLevel(logging.DEBUG)
        saved_handlers, saved_level = client_logger.handlers[:], client_logger.level
        client_logger.handlers = [collector]
        client_logger.setLevel(logging.DEBUG)
        try:
            await processor._handle_message(message)
        finally:
            client_logger.handlers = saved_handlers
            client_logger.setLevel(saved_level)

        texts = [record.getMessage() for record in captured]
        self.assertFalse(any(committed in t for t in texts), texts)
        self.assertFalse(any(tentative in t for t in texts), texts)


class _FakeCorrector:
    """让热词阶段保持输入原样，隔离结果流而非热词算法（与 test_editor_result_flow 同构）。"""

    def correct(self, text, k):
        return type('Correction', (), {'text': text, 'matchs': [], 'similars': []})()

    def substitute(self, text):
        return text


class _FakeHotword:
    def get_phoneme_corrector(self):
        return _FakeCorrector()

    def get_rule_corrector(self):
        return _FakeCorrector()


class _FakeState:
    """final 分支需要的最小 state：trace/audio 查询与 editor_last_case 赋值。"""

    def __init__(self):
        self.editor_last_case = None
        self.paste_target = None

    def pop_trace_context_by_task_id(self, task_id):
        return None

    def pop_audio_file(self, task_id):
        return None


def _new_result_processor(loop):
    """构造一个走真实代码路径、但输出侧整体打桩的 ResultProcessor。"""
    from core.client.output.result_processor import ResultProcessor
    app = types.SimpleNamespace(loop=loop, state=_FakeState(), hotword=_FakeHotword())
    processor = ResultProcessor(app)
    processor._emit_text = AsyncMock(return_value=True)  # 输出侧打桩：不粘贴、不打字
    return processor, app


class LivePanelTests(unittest.IsolatedAsyncioTestCase):
    """B12：真实 NSPanel 契约（非激活、样式、颜色）与 hide/auto-hide 行为。

    `core.client.output.live_panel` 是本变更的新文件；在基线提交上它还不存在，
    这里的导入会在 setUpClass 阶段以 ImportError 失败——这是“新模块以导入失败
    计入先失败”的允许形式，不需要额外用 skip 掩盖。
    """

    @classmethod
    def setUpClass(cls):
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        from core.client.output import live_panel
        cls.live_panel = live_panel
        # accessory 策略：面板可以显示，但本测试进程不应抢占用户当前的前台应用。
        cls.ns_app = NSApplication.sharedApplication()
        cls.ns_app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    def tearDown(self):
        # 真机面板测试用例结束后必须隐藏，不在屏幕上留下浮动面板。
        self.live_panel.hide()
        _pump_main_runloop(0.05)

    async def test_preview_message_updates_real_panel(self):
        """B12 生产入口
        Given: 服务端真实构造的预览消息（preview=True，committed + tentative），
               经 to_json/from_dict 往返
        When: 交给真实 ResultProcessor._handle_message，并把主线程 RunLoop 推进
        Then: 真实 live_panel 弹出非激活面板：不可成为 key window、忽略鼠标事件、
              不因失活隐藏；已提交文本用 labelColor，暂定文本用 secondaryLabelColor
        """
        from AppKit import (
            NSColor, NSForegroundColorAttributeName, NSWindowStyleMaskNonactivatingPanel,
        )

        committed, tentative = '你好', '世界'
        raw = RecognitionMessage(
            task_id='preview-panel', is_final=False, duration=1.0, time_start=0.0,
            time_submit=0.5, time_complete=0.6, text=committed,
            preview=True, text_tentative=tentative,
        ).to_json()
        message = RecognitionMessage.from_dict(json.loads(raw))

        processor, _app = _new_result_processor(asyncio.get_running_loop())
        await processor._handle_message(message)
        _pump_main_runloop(0.2)

        panel = self.live_panel._panel
        self.assertIsNotNone(panel, '首次 show 后必须已创建面板')
        self.assertTrue(panel.isVisible())
        self.assertTrue(bool(panel.styleMask() & NSWindowStyleMaskNonactivatingPanel))
        self.assertFalse(panel.canBecomeKeyWindow(), '面板不得夺走目标 App 的键盘焦点')
        self.assertTrue(panel.ignoresMouseEvents())
        self.assertFalse(panel.hidesOnDeactivate(), 'CapsWriter 本就不是前台 App')

        label = self.live_panel._label
        attributed = label.attributedStringValue()
        committed_color, _ = attributed.attribute_atIndex_effectiveRange_(
            NSForegroundColorAttributeName, 0, None)
        tentative_color, _ = attributed.attribute_atIndex_effectiveRange_(
            NSForegroundColorAttributeName, len(committed), None)
        self.assertEqual(committed_color, NSColor.labelColor())
        self.assertEqual(tentative_color, NSColor.secondaryLabelColor())

    async def test_final_hides_panel(self):
        """B12
        Given: 面板已因预览消息显示
        When: 收到该任务的 final 消息（输出侧整体打桩，不真实粘贴/打字）
        Then: _handle_message 在真正输出前调用 live_panel.hide()，面板不再可见
        """
        processor, _app = _new_result_processor(asyncio.get_running_loop())

        preview_raw = RecognitionMessage(
            task_id='preview-then-final', is_final=False, duration=1.0, time_start=0.0,
            time_submit=0.5, time_complete=0.6, text='已提交',
            preview=True, text_tentative='暂定',
        ).to_json()
        preview_message = RecognitionMessage.from_dict(json.loads(preview_raw))
        await processor._handle_message(preview_message)
        _pump_main_runloop(0.2)
        self.assertTrue(self.live_panel._panel.isVisible(), '前置条件：预览应已弹出面板')

        final_message = RecognitionMessage(
            task_id='preview-then-final', is_final=True, duration=1.0, time_start=0.0,
            time_submit=0.5, time_complete=0.6, text='最终文本',
        )
        with patch.multiple(Config, editor_mode=False, llm_enabled=False,
                             save_audio=False, hot=False), \
                patch('core.client.output.result_processor.get_active_window_info',
                      return_value={}):
            await processor._handle_message(final_message)
        _pump_main_runloop(0.2)

        self.assertFalse(self.live_panel._panel.isVisible(), 'final 到达后面板必须隐藏')

    async def test_panel_auto_hides(self):
        """B12
        Given: AUTO_HIDE 被临时调小（测试后恢复）
        When: 显示一次预览后不再有任何更新
        Then: 面板在 AUTO_HIDE 秒后自行隐藏（覆盖短按/取消录音、没有 final 到达的场景）
        """
        with patch.object(self.live_panel, 'AUTO_HIDE', 0.5):
            self.live_panel.show('自动隐藏', '')
            _pump_main_runloop(0.15)  # 远小于 AUTO_HIDE，验证还没到点就不会提前隐藏
            self.assertTrue(self.live_panel._panel.isVisible(), '前置条件：show 后、AUTO_HIDE 前应可见')
            _pump_main_runloop(0.6)  # 累计已超过 AUTO_HIDE(0.5s)
            self.assertFalse(self.live_panel._panel.isVisible(), '超过 AUTO_HIDE 后必须自动隐藏')


if __name__ == '__main__':
    unittest.main(verbosity=2)
