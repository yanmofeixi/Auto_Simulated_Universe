"""屏幕截图和窗口管理模块.

该模块负责:
- 获取游戏窗口截图
- 等待游戏窗口激活
- 管理截图相关的状态
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import numpy as np
import win32gui

if TYPE_CHECKING:
    from utils.screenshot import Screen


class ScreenManager:
    """屏幕截图管理器.

    负责获取游戏窗口截图,并处理窗口激活等待逻辑.

    Attributes:
        screen: 最近一次截取的屏幕图像
        sct: 截图工具实例
        x0, y0: 游戏窗口左上角坐标
        _stop: 停止标志
    """

    # 支持的游戏窗口标题
    GAME_WINDOW_TITLES = ("崩坏：星穹铁道", "云·星穹铁道")

    def __init__(
        self,
        sct: "Screen",
        x0: int,
        y0: int,
        log,
        stop_flag_getter=None,
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
        self.screen: np.ndarray | None = None

    @property
    def _stop(self) -> bool:
        """获取停止标志."""
        return self._stop_flag_getter()

    def _is_game_window_active(self) -> bool:
        """检查游戏窗口是否为当前活动窗口.

        Returns:
            True 如果游戏窗口是活动窗口
        """
        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        return window_title in self.GAME_WINDOW_TITLES

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

    def get_screen(self) -> np.ndarray:
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
        screen: np.ndarray,
        x_ratio: float,
        y_ratio: float,
        size: tuple[int, int],
        window_width: int,
        window_height: int,
        large: bool = True,
    ) -> np.ndarray:
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
