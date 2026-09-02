"""Windows 原生窗口特效：亚克力毛玻璃、圆角、无边框拖拽与缩放。"""

from __future__ import annotations

import ctypes
import platform
from ctypes import POINTER, byref, c_int, c_size_t, c_uint, wintypes

IS_WIN = platform.system() == "Windows"

if IS_WIN:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
else:  # pragma: no cover
    user32 = dwmapi = None

# 常量
WM_NCHITTEST = 0x0084
HTCLIENT = 1
HTCAPTION = 2
HTLEFT, HTRIGHT, HTTOP = 10, 11, 12
HTTOPLEFT, HTTOPRIGHT = 13, 14
HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 15, 16, 17

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWM_WINDOW_CORNER_ROUND = 2

WCA_ACCENT_POLICY = 19
ACCENT_DISABLED = 0
ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", c_int),
        ("AccentFlags", c_int),
        ("GradientColor", c_uint),
        ("AnimationId", c_int),
    ]


class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", c_int),
        ("Data", POINTER(ACCENT_POLICY)),
        ("SizeOfData", c_size_t),
    ]


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", c_int),
        ("cxRightWidth", c_int),
        ("cyTopHeight", c_int),
        ("cyBottomHeight", c_int),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


def _hwnd(widget) -> int:
    return int(widget.winId())


def msg_from_address(addr: int) -> "MSG":
    """把 Qt nativeEvent 传来的地址转成 MSG 结构。"""
    return ctypes.cast(addr, ctypes.POINTER(MSG)).contents


def c_short(value: int) -> int:
    return ctypes.c_short(value & 0xFFFF).value


def set_dark_mode(enabled: bool) -> None:
    if not IS_WIN:
        return
    try:
        hwnd = 0
        val = c_int(1 if enabled else 0)
        # 对本进程窗口无效，保留接口
        del hwnd, val
    except Exception:
        pass


def apply_window_theme(hwnd: int) -> None:
    """Win11 圆角 + 强制浅色模式。"""
    if not IS_WIN:
        return
    try:
        val = c_int(DWM_WINDOW_CORNER_ROUND)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, byref(val), ctypes.sizeof(val))
        dark = c_int(0)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(dark), ctypes.sizeof(dark))
    except Exception:
        pass


def apply_acrylic(hwnd: int, rgba: tuple[int, int, int, int] = (246, 248, 252, 190),
                  extend_frame: bool = True) -> bool:
    """启用亚克力毛玻璃。rgba 为 (R,G,B,A)。返回是否成功。"""
    if not IS_WIN:
        return False
    try:
        if extend_frame:
            m = MARGINS(-1, -1, -1, -1)
            dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(m))
        r, g, b, a = rgba
        gradient = (a << 24) | (b << 16) | (g << 8) | r  # ABGR
        accent = ACCENT_POLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2  # 允许透明渐变
        accent.GradientColor = gradient
        data = WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = POINTER(ACCENT_POLICY)(accent)
        data.SizeOfData = ctypes.sizeof(accent)
        ok = user32.SetWindowCompositionAttribute(hwnd, byref(data))
        return bool(ok)
    except Exception:
        return False


def disable_acrylic(hwnd: int) -> None:
    if not IS_WIN:
        return
    try:
        accent = ACCENT_POLICY()
        accent.AccentState = ACCENT_DISABLED
        data = WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = POINTER(ACCENT_POLICY)(accent)
        data.SizeOfData = ctypes.sizeof(accent)
        user32.SetWindowCompositionAttribute(hwnd, byref(data))
        m = MARGINS(0, 0, 0, 0)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(m))
    except Exception:
        pass


def nchittest(widget, lparam: int, border: int, caption_h: int, maximized: bool) -> int:
    from PySide6.QtCore import QPoint

    x = ctypes.c_short(lparam & 0xFFFF).value
    y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
    pos = widget.mapFromGlobal(QPoint(x, y))
    w, h = widget.width(), widget.height()
    if maximized:
        return HTCLIENT
    left = pos.x() < border
    right = pos.x() > w - border
    top = pos.y() < border
    bottom = pos.y() > h - border
    if left and top:
        return HTTOPLEFT
    if right and top:
        return HTTOPRIGHT
    if left and bottom:
        return HTBOTTOMLEFT
    if right and bottom:
        return HTBOTTOMRIGHT
    if left:
        return HTLEFT
    if right:
        return HTRIGHT
    if top:
        return HTTOP
    if bottom:
        return HTBOTTOM
    if pos.y() < caption_h:
        return HTCAPTION
    return HTCLIENT
