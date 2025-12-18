"""寻路导航模块.

该模块负责:
- 小地图导航
- 路径规划
- 移动控制
"""

from __future__ import annotations

import math
import threading
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Callable

import cv2 as cv
import numpy as np
import pyautogui

if TYPE_CHECKING:
    from diver.map_matcher import MapMatcher
    from diver.image_utils import EndPointDetector, InteractionPointDetector


class PathNavigator:
    """路径导航器.

    负责小地图导航和路径规划.

    Attributes:
        map_matcher: 地图匹配器实例
        end_detector: 终点检测器实例
        interaction_detector: 交互点检测器实例
    """

    def __init__(
        self,
        map_matcher: "MapMatcher",
        end_detector: "EndPointDetector",
        interaction_detector: "InteractionPointDetector",
        keyops,
        log,
    ):
        """初始化路径导航器.

        Args:
            map_matcher: 地图匹配器
            end_detector: 终点检测器
            interaction_detector: 交互点检测器
            keyops: 按键操作模块
            log: 日志记录器
        """
        self.map_matcher = map_matcher
        self.end_detector = end_detector
        self.interaction_detector = interaction_detector
        self.keyops = keyops
        self.log = log

        # 导航状态
        self.target: list = []  # 目标点列表
        self.last: tuple = (0, 0)  # 上一个完成的目标点
        self.lst_changed: float = 0  # 上次目标变更时间
        self.lst_tm: float = 0  # 上次到达时间

        # 移动控制
        self.stop_move: bool = False
        self.move: bool = False
        self.ready: bool = False
        self.is_target: int = 0
        self.ang_off: float = 0
        self.ang_neg: bool = False

    def get_target(self) -> tuple:
        """获取最近的目标点.

        Returns:
            (目标位置, 目标类型)
        """
        min_distance = 100000
        best_loc = (0, 0)
        best_type = -1

        for loc, target_type in self.target:
            distance = self.map_matcher.get_distance(loc, self.map_matcher.real_loc)
            if distance < min_distance:
                min_distance = distance
                best_loc = loc
                best_type = target_type

        # 如果找不到目标,使用上一个完成的目标点
        if best_loc == (0, 0):
            best_loc = self.last
            best_type = 3

        return best_loc, best_type

    def calculate_angle_to_target(self, target_loc: tuple) -> float:
        """计算到目标点需要旋转的角度.

        Args:
            target_loc: 目标位置

        Returns:
            需要旋转的角度
        """
        # 计算方向角
        target_angle = (
            math.atan2(
                target_loc[0] - self.map_matcher.real_loc[0],
                target_loc[1] - self.map_matcher.real_loc[1],
            )
            / math.pi
            * 180
        )

        # 计算与当前视角的差值
        angle_diff = target_angle - self.map_matcher.ang

        # 归一化到 [-180, 180]
        while angle_diff < -180:
            angle_diff += 360
        while angle_diff > 180:
            angle_diff -= 360

        return angle_diff

    def move_to_end(
        self,
        get_screen_fn: Callable,
        get_local_fn: Callable,
        mouse_move_fn: Callable,
        iteration: int = 0,
    ) -> int:
        """向终点移动.

        Args:
            get_screen_fn: 获取屏幕截图的函数
            get_local_fn: 获取局部区域的函数
            mouse_move_fn: 鼠标移动函数
            iteration: 迭代次数

        Returns:
            1 表示成功找到终点,0 表示失败
        """
        get_screen_fn()
        dx = self.end_detector.get_end_point(None, get_local_fn, mask=iteration)

        if dx is None:
            if iteration:
                return 0

            # 尝试调整视角后重新检测
            import win32api
            import win32con

            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -200)
            time.sleep(0.3)

            dx = self.end_detector.get_end_point(None, get_local_fn)

            if dx is None:
                # 尝试多个角度
                angles = [60, 120, 60, 60, 30, -60, -60, -60, -60]
                offset = 0

                for angle in angles:
                    if self.ang_neg:
                        mouse_move_fn(angle)
                        offset -= angle
                    else:
                        mouse_move_fn(-angle)
                        offset += angle

                    time.sleep(0.3)
                    dx = self.end_detector.get_end_point(None, get_local_fn)

                    if dx is not None:
                        break

                if dx is None:
                    mouse_move_fn(offset * 1.03)
                    time.sleep(0.3)
                    return 0

        # 根据迭代次数调整移动量
        if iteration == 0:
            mouse_move_fn(dx / 3)
            time.sleep(0.3)

            if abs(dx / 3) > 30:
                time.sleep(0.3)
                dx = self.end_detector.get_end_point(None, get_local_fn, mask=1)
                if dx is not None:
                    mouse_move_fn(dx / 4)
                    time.sleep(0.3)
        else:
            mouse_move_fn(dx / 5)
            time.sleep(0.3)

        return 1

    def move_to_interaction(
        self,
        get_screen_fn: Callable,
        get_local_fn: Callable,
        mouse_move_fn: Callable,
        floor: int,
        scx: float,
        icon_index: int = 0,
    ) -> float:
        """向交互点移动.

        Args:
            get_screen_fn: 获取屏幕截图的函数
            get_local_fn: 获取局部区域的函数
            mouse_move_fn: 鼠标移动函数
            floor: 当前楼层
            scx: 缩放系数
            icon_index: 图标索引

        Returns:
            视角旋转角度
        """
        get_screen_fn()
        shape = (int(scx * 190), int(scx * 190))
        current_loc = (118 + 2, 125 + 2)

        local_screen = get_local_fn(0.9333, 0.8657, shape)

        # 查找交互点
        target_info = self.interaction_detector.find_interaction_point(
            local_screen, floor, icon_index
        )

        if target_info["type"] >= 1:
            # 获取当前视角角度
            from utils.common.minimap_ops import get_now_direc

            current_angle = 360 - get_now_direc(cv, local_screen, "imgs/loc_arrow.jpg") - 90

            # 计算需要旋转的角度
            target_angle = (
                math.atan2(
                    target_info["position"][0] - current_loc[0],
                    target_info["position"][1] - current_loc[1],
                )
                / math.pi
                * 180
            )

            angle_diff = target_angle - current_angle

            # 归一化角度
            while angle_diff < -180:
                angle_diff += 360
            while angle_diff > 180:
                angle_diff -= 360

            if angle_diff == 0:
                angle_diff = 1e-9

            if icon_index == 0:
                angle_diff = 0

            if not self.stop_move:
                mouse_move_fn(angle_diff)
                return angle_diff

        return 0

    def keep_move(self, press_fn: Callable, stop_flag_getter: Callable) -> None:
        """保持移动状态.

        在移动过程中交替按下 W 和 S 键.

        Args:
            press_fn: 按键函数
            stop_flag_getter: 获取停止标志的回调
        """
        keys = "ws"
        index = 0

        while self.move and not stop_flag_getter():
            press_fn(keys[index], 0.05)
            time.sleep(0.08)
            index ^= 1

        if not stop_flag_getter():
            self.keyops.keyDown("w")
