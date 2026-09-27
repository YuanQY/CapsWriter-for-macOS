# coding: utf-8
"""
实时预览面板（PyObjC，2026-09 live 听写模式）：live 模式下把已提交/待定文本
显示在这块悬浮面板里。面板不可编辑、不接收输入，用 NonactivatingPanel +
orderFrontRegardless（从不 makeKeyAndOrderFront_、不激活本 App、类本身也不
覆写 canBecomeKeyWindow）保证不抢目标应用的焦点。收到最终结果或 5 秒无新
show() 后自动收起（generation 计数器防止过期的 callLater 关掉更晚的面板）。

show()/hide() 可在任意线程调用，经 AppHelper.callAfter 派发到主线程。本 fork
只跑 macOS，PyObjC 恒随 AppKit 客户端依赖到场，故不像 edit_panel 那样做导入
兜底；但在 start_client.py 之外（例如无 NSApp 主 RunLoop 的场景）调用
show()/hide() 时，callAfter 派发的任务不会被执行，面板也就不会出现。
"""
from __future__ import annotations

from AppKit import (
    NSPanel, NSView, NSTextField, NSFont, NSColor, NSScreen,
    NSFloatingWindowLevel, NSWindowStyleMaskNonactivatingPanel,
    NSBackingStoreBuffered,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSVisualEffectView, NSVisualEffectMaterialPopover,
    NSVisualEffectBlendingModeBehindWindow, NSVisualEffectStateActive,
    NSMutableAttributedString, NSAttributedString,
    NSForegroundColorAttributeName, NSFontAttributeName,
)
from Foundation import NSRect, NSPoint, NSSize
from PyObjCTools import AppHelper

from core.client.output.edit_panel import (
    _PANEL_W, _MARGIN, _CORNER_RADIUS, panel_origin_y,
)

AUTO_HIDE = 5.0        # 秒：最后一次 show() 之后无新更新，面板自动收起
_FONT_SIZE = 15.0
_MIN_LABEL_H = 20.0    # 单行文本的最小高度

_panel = None          # NSPanel，首次 show() 时创建；供测试读取
_label = None          # NSTextField，展示带颜色的识别文本；供测试读取
_effect = None         # 毛玻璃底（内部实现，非契约的一部分）
_generation = 0        # 自增代：callLater 触发时若已被更晚的 show() 取代则不隐藏


def show(committed: str, tentative: str) -> None:
    """任意线程可调用：显示/更新预览文本，并重置 5 秒自动隐藏计时。"""
    AppHelper.callAfter(_show_on_main, committed, tentative)


def hide() -> None:
    """任意线程可调用：立即隐藏面板；从未 show() 过时是空操作。"""
    AppHelper.callAfter(_hide_on_main)


def _show_on_main(committed: str, tentative: str) -> None:
    global _panel, _label, _effect, _generation
    if _panel is None:
        size = NSSize(_PANEL_W, _MIN_LABEL_H + 2 * _MARGIN)
        _panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSRect(NSPoint(0, 0), size), NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered, False)
        _panel.setOpaque_(False)
        _panel.setBackgroundColor_(NSColor.clearColor())
        _panel.setHasShadow_(True)
        _panel.setLevel_(NSFloatingWindowLevel)
        # CapsWriter 从不是前台 App；默认 hidesOnDeactivate 会让面板随之隐藏。
        _panel.setHidesOnDeactivate_(False)
        _panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary)
        _panel.setIgnoresMouseEvents_(True)  # 纯展示，不拦截鼠标事件

        clip_view = NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), size))
        clip_view.setWantsLayer_(True)
        clip_view.layer().setCornerRadius_(_CORNER_RADIUS)
        clip_view.layer().setMasksToBounds_(True)
        _panel.setContentView_(clip_view)

        _effect = NSVisualEffectView.alloc().initWithFrame_(clip_view.bounds())
        _effect.setMaterial_(NSVisualEffectMaterialPopover)
        _effect.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        _effect.setState_(NSVisualEffectStateActive)
        _effect.setWantsLayer_(True)
        _effect.layer().setCornerRadius_(_CORNER_RADIUS)
        _effect.layer().setMasksToBounds_(True)
        clip_view.addSubview_(_effect)

        _label = NSTextField.alloc().initWithFrame_(
            NSRect(NSPoint(_MARGIN, _MARGIN),
                   NSSize(_PANEL_W - 2 * _MARGIN, _MIN_LABEL_H)))
        _label.setEditable_(False)
        _label.setSelectable_(False)
        _label.setBezeled_(False)
        _label.setBordered_(False)
        _label.setDrawsBackground_(False)
        _label.cell().setWraps_(True)   # 多行自动换行；lineBreakMode 默认已是按词换行
        _label.setUsesSingleLineMode_(False)
        _effect.addSubview_(_label)

    # 已提交/待定两段分别建带属性的字符串再拼接，不用下标切原始 NSRange：
    # NSString 按 UTF-16 计数，Python len() 对含表情等非 BMP 字符的文本会数少，
    # 拼接方式不依赖长度换算，任何字符都不会漏上色。
    font = NSFont.systemFontOfSize_(_FONT_SIZE)
    attr = NSMutableAttributedString.alloc().initWithString_attributes_(
        committed, {NSFontAttributeName: font,
                    NSForegroundColorAttributeName: NSColor.labelColor()})
    attr.appendAttributedString_(
        NSAttributedString.alloc().initWithString_attributes_(
            tentative, {NSFontAttributeName: font,
                        NSForegroundColorAttributeName: NSColor.secondaryLabelColor()}))
    _label.setAttributedStringValue_(attr)

    # 按内容定高；固定上边缘，面板只向下伸展或从下边缩回（同 edit_panel）。
    # 用 cell().cellSizeForBounds_ 量高度，而非 attr.boundingRectWithSize_options_：
    # 后者按整宽排版，比 NSTextField 实际可用宽度更宽，换行点会算少一行，
    # 导致混排中英文时最后一行（最新的待定文字）被裁掉。
    width = _PANEL_W - 2 * _MARGIN
    text_h = max(_MIN_LABEL_H, _label.cell().cellSizeForBounds_(
        NSRect(NSPoint(0, 0), NSSize(width, 1.0e7))).height)
    content_h = text_h + 2 * _MARGIN

    screen = NSScreen.mainScreen().visibleFrame()
    x = screen.origin.x + (screen.size.width - _PANEL_W) / 2
    y = panel_origin_y(content_h, screen.origin.y, screen.size.height)

    _label.setFrame_(NSRect(NSPoint(_MARGIN, _MARGIN), NSSize(width, text_h)))
    _panel.setFrame_display_(
        NSRect(NSPoint(x, y), NSSize(_PANEL_W, content_h)), True)
    _effect.setFrame_(_panel.contentView().bounds())

    _panel.orderFrontRegardless()  # 只前置显示，绝不 makeKey、绝不激活本 App
    _generation += 1
    gen = _generation
    AppHelper.callLater(AUTO_HIDE, _auto_hide, gen)


def _hide_on_main() -> None:
    if _panel is not None:
        _panel.orderOut_(None)


def _auto_hide(gen: int) -> None:
    if gen == _generation:  # 期间已有更晚的 show()，本次超时作废
        _hide_on_main()
