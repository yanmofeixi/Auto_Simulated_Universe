"""图像处理工具模块.

该模块负责:
- 图像旋转变换
- 终点检测
- 交互点识别
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

import cv2 as cv
import numpy as np

if TYPE_CHECKING:
    pass


class ImageProcessor:
    """图像处理器.

    提供图像变换,区域检测等功能.
    """

    @staticmethod
    def handle_rotate_matrix(x: int, y: int, rotate: float) -> np.ndarray:
        """计算以指定点为中心的旋转变换矩阵.

        Args:
            x: 旋转中心 X 坐标
            y: 旋转中心 Y 坐标
            rotate: 旋转角度(度)

        Returns:
            2x3 的仿射变换矩阵
        """
        cos_val = np.cos(np.deg2rad(rotate))
        sin_val = np.sin(np.deg2rad(rotate))
        return np.float32([
            [cos_val, sin_val, x * (1 - cos_val) - y * sin_val],
            [-sin_val, cos_val, x * sin_val + y * (1 - cos_val)],
        ])

    @staticmethod
    def rotate_image(src: np.ndarray, rotate: float = 0) -> np.ndarray:
        """以图像中心为轴旋转图像.

        Args:
            src: 源图像
            rotate: 旋转角度(度)

        Returns:
            旋转后的图像
        """
        h, w, c = src.shape
        matrix = ImageProcessor.handle_rotate_matrix(w // 2, h // 2, rotate)
        return cv.warpAffine(src, matrix, (w, h))


class EndPointDetector:
    """终点检测器.

    用于检测小地图中的终点位置.
    """

    # 颜色常量
    COLOR_BLACK = np.array([0, 0, 0])
    COLOR_WHITE = np.array([255, 255, 255])

    def __init__(self, region_template_path: str = "imgs/region.jpg"):
        """初始化终点检测器.

        Args:
            region_template_path: 区域标识模板图像路径
        """
        self.region_template = cv.imread(region_template_path, cv.IMREAD_GRAYSCALE)

    def get_end_point(
        self,
        screen: np.ndarray,
        get_local_fn,
        mask: int = 0,
    ) -> float | None:
        """检测终点相对于屏幕中心的偏移.

        Args:
            screen: 屏幕截图
            get_local_fn: 获取局部区域的函数
            mask: 掩码范围限制

        Returns:
            终点的水平偏移量,或 None 如果未检测到
        """
        local_screen = get_local_fn(0.4979, 0.6296, (715, 1399))

        # 创建黑白掩码
        bw_map = np.zeros(local_screen.shape[:2], dtype=np.uint8)

        # 检测黑色像素
        black_mask = deepcopy(bw_map)
        black_mask[
            np.sum((local_screen - self.COLOR_BLACK) ** 2, axis=-1) <= 1600
        ] = 255

        # 检测白色像素
        white_mask = deepcopy(bw_map)
        white_mask[
            np.sum((local_screen - self.COLOR_WHITE) ** 2, axis=-1) <= 1600
        ] = 255

        # 膨胀黑色区域
        kernel = np.ones((7, 7), np.uint8)
        black_mask = cv.dilate(black_mask, kernel, iterations=1)

        # 合并黑白区域
        bw_map[(black_mask > 200) & (white_mask > 200)] = 255

        # 应用掩码限制搜索范围
        center = 660
        if mask:
            try:
                bw_map[:, : center - 350 // mask] = 0
                bw_map[:, center + 350 // mask :] = 0
            except:
                pass

        # 模板匹配
        result = cv.matchTemplate(bw_map, self.region_template, cv.TM_CCORR_NORMED)
        _, max_val, _, max_loc = cv.minMaxLoc(result)

        if max_val < 0.6:
            return None

        # 计算偏移量(使用幂函数平滑)
        dx = max_loc[0] - center
        if dx > 0:
            return dx ** 0.7
        else:
            return -((-dx) ** 0.7)


class InteractionPointDetector:
    """交互点检测器.

    用于在小地图中检测可交互的目标点.
    """

    # 颜色常量
    COLOR_BLUE = np.array([234, 191, 4])
    COLOR_RED = np.array([60, 60, 226])

    def __init__(self, format_path_fn):
        """初始化交互点检测器.

        Args:
            format_path_fn: 格式化图像路径的函数
        """
        self.format_path = format_path_fn

    def find_interaction_point(
        self,
        local_screen: np.ndarray,
        floor: int,
        icon_index: int = 0,
        threshold: float = 0.88,
    ) -> dict:
        """在小地图中查找交互点.

        Args:
            local_screen: 小地图截图
            floor: 当前楼层
            icon_index: 图标索引
            threshold: 匹配阈值

        Returns:
            包含目标位置和类型的字典
        """
        current_loc = (118 + 2, 125 + 2)
        target = {"position": (-1, -1), "type": 0, "floor": floor}

        # 尝试匹配主要交互点图标
        icon_path = self.format_path(f"mini{icon_index + 1}")
        icon = cv.imread(icon_path)

        if icon is not None:
            result = cv.matchTemplate(local_screen, icon, cv.TM_CCORR_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)

            if max_val > threshold:
                sp = icon.shape
                target["position"] = (
                    max_loc[1] + sp[0] // 2,
                    max_loc[0] + sp[1] // 2,
                )
                target["type"] = 1
                if floor >= 12:
                    target["floor"] = 11
                return target

        # 尝试匹配次要交互点图标(如黑塔)
        icon_path = self.format_path(f"mini{icon_index + 2}")
        icon = cv.imread(icon_path)

        if icon is not None:
            # 特定楼层降低阈值
            adjusted_threshold = threshold - 0.035 * (floor in [4, 8, 11])
            result = cv.matchTemplate(local_screen, icon, cv.TM_CCORR_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)

            if max_val > adjusted_threshold:
                sp = icon.shape
                target["position"] = (
                    max_loc[1] + sp[0] // 2,
                    max_loc[0] + sp[1] // 2,
                )
                target["type"] = 2
                if floor >= 12:
                    target["floor"] = 11
                return target

        # 清除圆形区域外的像素
        for i in range(local_screen.shape[0]):
            for j in range(local_screen.shape[1]):
                if self._get_distance((120, 128), (i, j)) >= 82:
                    local_screen[i, j] = [0, 0, 0]

        # 尝试检测红色标记点
        red_pixels = np.where(
            np.sum((local_screen - self.COLOR_RED) ** 2, axis=-1) <= 512
        )

        if red_pixels[0].shape[0] > 0:
            target["position"] = (red_pixels[0][0], red_pixels[1][0])
            target["type"] = 3
            if floor == 11:
                target["floor"] = 12

        return target

    @staticmethod
    def _get_distance(point1: tuple, point2: tuple) -> float:
        """计算两点距离."""
        return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5
