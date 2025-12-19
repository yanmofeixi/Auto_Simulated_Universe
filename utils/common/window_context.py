"""Windows 游戏窗口上下文(diver/simul 共享).

目标:
- 统一 diver/simul 在 UniverseUtils.__init__ 里对窗口坐标,缩放,DPI 的计算
- 把一大段重复的 win32 逻辑抽出来,减少两边维护成本

设计原则:
- 复用 window.py 中的 set_game_foreground 查找并激活游戏窗口
- 只负责计算上下文;是否报错/如何日志由调用方决定
"""

from __future__ import annotations

import time

from dataclasses import dataclass


@dataclass(frozen=True)
class GameWindowContext:
    """游戏窗口计算结果."""

    hwnd: int
    title: str

    # WindowRect:屏幕坐标系下窗口左上右下
    x0: int
    y0: int
    x1: int
    y1: int

    # 逻辑窗口宽高(用于坐标换算),这里会被裁剪到 1920x1080(若满足条件)
    width: int
    height: int

    # 是否全屏(用来决定 +9px 的历史偏移)
    is_fullscreen: bool

    # 相对基准分辨率(1920x1080)的缩放比例
    scx: float
    scy: float

    # DPI 缩放(GetDpiForWindow / 96)
    dpi_scale: float

    # 真实分辨率推算(仅用于历史兼容日志/调试)
    real_width: int


def wait_for_game_window_context(
    *,
    primary_title: str = "崩坏：星穹铁道",
    secondary_title: str = "云.星穹铁道",
    window_class: str = "UnityWndClass",
    baseline_width: int = 1920,
    baseline_height: int = 1080,
    fullscreen_offset_px: int = 9,
    poll_interval_s: float = 0.3,
    log=None,
) -> GameWindowContext:
    """查找游戏窗口并返回上下文.

    复用 window.py 中的 set_game_foreground 查找并激活游戏窗口.
    """

    import ctypes

    import win32con
    import win32gui
    import win32print

    from utils.common.window import set_game_foreground

    while True:
        try:
            # 使用 window.py 中的函数查找并激活游戏窗口
            hwnd = set_game_foreground(
                primary_title=primary_title,
                secondary_title=secondary_title,
                window_class=window_class,
            )

            if hwnd is None or hwnd == 0:
                # 游戏窗口未找到,继续等待
                time.sleep(poll_interval_s)
                continue

            time.sleep(0.1)  # 等待窗口切换

            # 获取窗口标题
            title = win32gui.GetWindowText(hwnd)

            # ClientRect:客户端区域坐标(相对窗口),用于计算宽高
            cx0, cy0, cx1, cy1 = win32gui.GetClientRect(hwnd)
            width = cx1 - cx0
            height = cy1 - cy0

            # WindowRect:窗口在屏幕上的坐标
            x0, y0, x1, y1 = win32gui.GetWindowRect(hwnd)
            is_fullscreen = x0 == 0 and y0 == 0

            # 历史兼容:全屏时会额外 +9 像素偏移
            x0 = max(0, x1 - width) + fullscreen_offset_px * int(is_fullscreen)
            y0 = max(0, y1 - height) + fullscreen_offset_px * int(is_fullscreen)

            # 如果窗口比基准分辨率大,则居中裁剪到 1920x1080
            if (
                (width == baseline_width or height == baseline_height)
                and width >= baseline_width
                and height >= baseline_height
            ):
                x0 += (width - baseline_width) // 2
                y0 += (height - baseline_height) // 2
                x1 -= (width - baseline_width) // 2
                y1 -= (height - baseline_height) // 2
                width, height = baseline_width, baseline_height

            scx = width / float(baseline_width)
            scy = height / float(baseline_height)

            # DPI/缩放
            dc = win32gui.GetWindowDC(hwnd)
            dpi_x = win32print.GetDeviceCaps(dc, win32con.LOGPIXELSX)
            win32gui.ReleaseDC(hwnd, dc)
            scale_x = dpi_x / 96.0

            try:
                dpi_scale = ctypes.windll.user32.GetDpiForWindow(hwnd) / 96.0
            except Exception:
                dpi_scale = 1.0
                if log is not None:
                    try:
                        log.info("DPI获取失败")
                    except Exception:
                        pass

            real_width = int(width * scale_x)

            return GameWindowContext(
                hwnd=int(hwnd),
                title=str(title),
                x0=int(x0),
                y0=int(y0),
                x1=int(x1),
                y1=int(y1),
                width=int(width),
                height=int(height),
                is_fullscreen=bool(is_fullscreen),
                scx=float(scx),
                scy=float(scy),
                dpi_scale=float(dpi_scale),
                real_width=int(real_width),
            )

        except Exception:
            # 异常时不终止,继续等待
            time.sleep(poll_interval_s)
            continue
