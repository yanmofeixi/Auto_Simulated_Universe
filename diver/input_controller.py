"""输入控制模块.

该模块负责:
- 鼠标移动和点击
- 键盘按键操作
- 视角旋转控制
"""

from __future__ import annotations

import time
from typing import Callable

import win32api
import win32con


class InputController:
    """输入控制器.

    封装键鼠输入操作,支持视角旋转,点击等功能.

    Attributes:
        multi: 鼠标灵敏度倍率
        scale: DPI 缩放比例
        stop_flag_getter: 获取停止标志的回调
        stop_move_flag_getter: 获取停止移动标志的回调
    """

    # 鼠标移动灵敏度系数
    MOUSE_SENSITIVITY = 16.5
    # 单次最大旋转角度
    MAX_ROTATION_ANGLE = 30

    def __init__(
        self,
        multi: float = 1.0,
        scale: float = 1.0,
        stop_flag_getter: Callable[[], bool] | None = None,
        stop_move_flag_getter: Callable[[], bool] | None = None,
    ):
        """初始化输入控制器.

        Args:
            multi: 鼠标灵敏度倍率
            scale: DPI 缩放比例
            stop_flag_getter: 获取全局停止标志的回调
            stop_move_flag_getter: 获取停止移动标志的回调
        """
        self.multi = multi
        self.scale = scale
        self._stop_flag_getter = stop_flag_getter or (lambda: False)
        self._stop_move_flag_getter = stop_move_flag_getter or (lambda: False)

    @property
    def _stop(self) -> bool:
        """获取全局停止标志."""
        return self._stop_flag_getter()

    @property
    def _stop_move(self) -> bool:
        """获取停止移动标志."""
        return self._stop_move_flag_getter()

    def mouse_move_raw(self, dx: int, dy: int = 0) -> None:
        """执行原始鼠标移动.

        Args:
            dx: X 方向移动像素数
            dy: Y 方向移动像素数
        """
        if not self._stop and not self._stop_move:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)

    def rotate_view(self, angle: float, fine: int = 1) -> None:
        """旋转游戏视角.

        将指定角度转换为鼠标移动量,并递归处理大角度旋转.

        Args:
            angle: 要旋转的角度(正值向右,负值向左)
            fine: 精细度系数(用于分割大角度旋转)

        Raises:
            ValueError: 当停止标志被设置时抛出
        """
        # 限制单次旋转的最大角度
        max_angle = self.MAX_ROTATION_ANGLE // fine

        if angle > max_angle:
            clamped_angle = max_angle
        elif angle < -max_angle:
            clamped_angle = -max_angle
        else:
            clamped_angle = angle

        # 计算鼠标移动量
        dx = int(self.MOUSE_SENSITIVITY * clamped_angle * self.multi * self.scale)

        # 执行移动
        self.mouse_move_raw(dx, 0)
        time.sleep(0.05 * fine)

        # 如果还有剩余角度,递归处理
        remaining = angle - clamped_angle
        if abs(remaining) > 0.001:
            if self._stop:
                raise ValueError("正在退出")
            self.rotate_view(remaining, fine)

    def move_vertical(self, dy: int) -> None:
        """垂直移动鼠标(用于调整视角俯仰).

        Args:
            dy: Y 方向移动像素数(正值向下,负值向上)
        """
        self.mouse_move_raw(0, dy)
