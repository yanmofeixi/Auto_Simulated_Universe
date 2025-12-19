"""Windows 游戏窗口管理模块.

该模块统一处理游戏窗口相关的所有操作:
- 查找并激活游戏窗口
- 等待游戏窗口成为前台
- 获取窗口坐标、缩放、DPI 等上下文信息

注意:
- 该仓库主要运行在 Windows;本模块依赖 pywin32(win32gui 等).
- 为了减少导入副作用,win32 相关库在函数内延迟导入.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional, TYPE_CHECKING

from utils.common.config_base import (
    BASELINE_HEIGHT,
    BASELINE_WIDTH,
    FULLSCREEN_OFFSET_PX,
    GAME_TITLE_PRIMARY,
    GAME_TITLE_SECONDARY,
    GAME_WINDOW_CLASS,
    is_game_window,
)

if TYPE_CHECKING:
    import numpy as np
    from utils.screenshot import Screen


# ===== 数据类 =====


@dataclass(frozen=True)
class GameWindowContext:
    """游戏窗口上下文信息.

    包含窗口坐标、缩放比例、DPI 等信息，用于初始化 UniverseUtils。
    """

    hwnd: int
    title: str

    # WindowRect: 屏幕坐标系下窗口左上右下
    x0: int
    y0: int
    x1: int
    y1: int

    # 逻辑窗口宽高(用于坐标换算)，会被裁剪到 1920x1080(若满足条件)
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


# ===== 窗口操作函数 =====


def set_game_foreground(
    *,
    primary_title: str = GAME_TITLE_PRIMARY,
    secondary_title: str = GAME_TITLE_SECONDARY,
    window_class: str = GAME_WINDOW_CLASS,
    is_frozen: bool = False,
) -> Optional[int]:
    """尝试将游戏窗口设为前台.

    Args:
        primary_title: 主要窗口标题
        secondary_title: 备用窗口标题
        window_class: 窗口类名
        is_frozen: 是否为打包后的可执行环境

    Returns:
        成功返回窗口句柄(int)，失败返回 None

    说明:
        与历史实现保持一致:通过 WScript.Shell.SendKeys 解除焦点锁定.
        若按 (class, title) 找不到,则回退到 (None, title).
    """
    try:
        import pythoncom
        import win32com.client
        import win32gui

        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys(" " if is_frozen else "")

        # 尝试用 class + title 查找
        hwnd = win32gui.FindWindow(window_class, primary_title)

        if hwnd == 0:
            # 回退:只用 title 查找
            hwnd = win32gui.FindWindow(None, secondary_title)

        if hwnd == 0:
            return None

        # 找到窗口,尝试设为前台
        win32gui.SetForegroundWindow(hwnd)
        return int(hwnd)

    except Exception:
        return None


def wait_for_game_foreground(
    *,
    stop_flag: Callable[[], bool],
    on_waiting: Optional[Callable[[str], None]] = None,
    on_lst_changed: Optional[Callable[[], None]] = None,
    set_foreground_fn: Optional[Callable[[], None]] = None,
    poll_interval: float = 0.5,
    foreground_retry_count: int = 1200,
) -> bool:
    """等待游戏窗口成为前台窗口.

    该函数会阻塞直到游戏窗口成为前台，或者 stop_flag 返回 True。

    Args:
        stop_flag: 返回是否应该停止等待的函数
        on_waiting: 首次开始等待时的回调，参数为当前窗口标题
        on_lst_changed: 每次轮询时的回调（用于更新 lst_changed 时间戳）
        set_foreground_fn: 尝试将游戏窗口设为前台的函数
        poll_interval: 轮询间隔（秒）
        foreground_retry_count: 多少次轮询后尝试调用 set_foreground_fn

    Returns:
        True 表示游戏窗口已成为前台，False 表示被 stop_flag 中断
    """
    import win32gui

    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    warned = False
    cnt = 0

    while not is_game_window(title) and not stop_flag():
        if on_lst_changed:
            on_lst_changed()

        if stop_flag():
            return False

        if not warned:
            warned = True
            if on_waiting:
                on_waiting(title)

        time.sleep(poll_interval)
        cnt += 1

        if cnt == foreground_retry_count and set_foreground_fn:
            set_foreground_fn()

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)

    return not stop_flag()


def wait_for_game_window_context(
    *,
    primary_title: str = GAME_TITLE_PRIMARY,
    secondary_title: str = GAME_TITLE_SECONDARY,
    window_class: str = GAME_WINDOW_CLASS,
    baseline_width: int = BASELINE_WIDTH,
    baseline_height: int = BASELINE_HEIGHT,
    fullscreen_offset_px: int = FULLSCREEN_OFFSET_PX,
    poll_interval_s: float = 0.3,
    log=None,
) -> GameWindowContext:
    """查找游戏窗口并返回上下文.

    会阻塞直到找到游戏窗口并成功获取上下文信息。

    Args:
        primary_title: 主要窗口标题
        secondary_title: 备用窗口标题
        window_class: 窗口类名
        baseline_width: 基准分辨率宽度
        baseline_height: 基准分辨率高度
        fullscreen_offset_px: 全屏时的像素偏移
        poll_interval_s: 轮询间隔（秒）
        log: 日志记录器

    Returns:
        GameWindowContext 包含窗口的所有上下文信息
    """
    import ctypes
    import win32con
    import win32gui
    import win32print

    while True:
        try:
            # 使用 set_game_foreground 查找并激活游戏窗口
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

            # ClientRect: 客户端区域坐标(相对窗口),用于计算宽高
            cx0, cy0, cx1, cy1 = win32gui.GetClientRect(hwnd)
            width = cx1 - cx0
            height = cy1 - cy0

            # WindowRect: 窗口在屏幕上的坐标
            x0, y0, x1, y1 = win32gui.GetWindowRect(hwnd)
            is_fullscreen = x0 == 0 and y0 == 0

            # 历史兼容: 全屏时会额外 +9 像素偏移
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


# ===== 屏幕管理类 =====


class ScreenManager:
    """屏幕截图管理器.

    负责获取游戏窗口截图,并处理窗口激活等待逻辑.

    Attributes:
        screen: 最近一次截取的屏幕图像
        sct: 截图工具实例
        x0, y0: 游戏窗口左上角坐标
    """

    def __init__(
        self,
        sct: "Screen",
        x0: int,
        y0: int,
        log,
        stop_flag_getter: Optional[Callable[[], bool]] = None,
    ):
        """初始化屏幕管理器.

        Args:
            sct: 截图工具实例
            x0: 游戏窗口左上角 X 坐标
            y0: 游戏窗口左上角 Y 坐标
            log: 日志记录器
            stop_flag_getter: 获取停止标志的回调函数
        """
        self.sct = sct
        self.x0 = x0
        self.y0 = y0
        self.log = log
        self._stop_flag_getter = stop_flag_getter or (lambda: False)
        self.screen: "np.ndarray | None" = None

    @property
    def _stop(self) -> bool:
        """获取停止标志."""
        return self._stop_flag_getter()

    def _is_game_window_active(self) -> bool:
        """检查游戏窗口是否为当前活动窗口.

        Returns:
            True 如果游戏窗口是活动窗口
        """
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        return is_game_window(window_title)

    def wait_for_game_window(self, timeout: float = 0) -> bool:
        """等待游戏窗口激活.

        Args:
            timeout: 超时时间(秒),0 表示无限等待

        Returns:
            True 如果成功等待到游戏窗口
        """
        start_time = time.time()

        while not self._is_game_window_active() and not self._stop:
            self.log.warning("等待游戏窗口")
            time.sleep(0.5)

            if timeout > 0 and time.time() - start_time > timeout:
                return False

        return not self._stop

    def get_screen(self) -> "np.ndarray":
        """获取游戏窗口截图.

        如果游戏窗口不是活动窗口,会阻塞等待直到游戏窗口激活.

        Returns:
            截取的屏幕图像(numpy 数组)
        """
        # 等待游戏窗口激活
        self.wait_for_game_window()

        # 截取屏幕
        self.screen = self.sct.grab(self.x0, self.y0)
        return self.screen

    def get_local_region(
        self,
        screen: "np.ndarray",
        x_ratio: float,
        y_ratio: float,
        size: tuple[int, int],
        window_width: int,
        window_height: int,
        large: bool = True,
    ) -> "np.ndarray":
        """从截图中裁剪指定区域.

        根据相对坐标和大小,从截图中裁剪出需要的区域.

        Args:
            screen: 完整的屏幕截图
            x_ratio: X 坐标比例(0-1,从右到左)
            y_ratio: Y 坐标比例(0-1,从下到上)
            size: 裁剪区域大小 (width, height)
            window_width: 窗口宽度
            window_height: 窗口高度
            large: 是否使用较大的裁剪区域

        Returns:
            裁剪后的图像区域
        """
        # 计算中心点坐标(从右下角开始计算)
        center_x = int(window_width * (1 - x_ratio))
        center_y = int(window_height * (1 - y_ratio))

        # 计算裁剪边界
        half_width = size[0] // 2
        half_height = size[1] // 2

        x_start = max(0, center_x - half_width)
        x_end = min(window_width, center_x + half_width)
        y_start = max(0, center_y - half_height)
        y_end = min(window_height, center_y + half_height)

        return screen[y_start:y_end, x_start:x_end]
