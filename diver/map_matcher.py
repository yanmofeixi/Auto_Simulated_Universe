"""地图匹配和定位模块.

该模块负责:
- 小地图与大地图的匹配
- 角色位置定位
- 地图特征提取
"""

from __future__ import annotations

from copy import deepcopy
from math import sin, cos
from typing import TYPE_CHECKING

import cv2 as cv
import numpy as np

if TYPE_CHECKING:
    pass


class MapMatcher:
    """地图匹配器.

    处理小地图与大地图之间的匹配,实现角色定位功能.

    Attributes:
        big_map: 大地图数据
        now_loc: 当前位置坐标
        real_loc: 真实位置坐标(考虑偏移)
        ang: 当前视角角度
    """

    # 颜色常量(BGR 格式)
    COLOR_GRAY = np.array([55, 55, 55])
    COLOR_WHITE = np.array([210, 210, 210])
    COLOR_BLACK = np.array([0, 0, 0])
    COLOR_YELLOW = np.array([145, 192, 220])
    COLOR_BLUE = np.array([234, 191, 4])

    def __init__(self):
        """初始化地图匹配器."""
        self.big_map: np.ndarray | None = None
        self.now_loc: tuple[int, int] = (0, 0)
        self.real_loc: tuple[int, int] = (0, 0)
        self.ang: float = 0.0
        self.loc_off: int = 0
        self.slow: bool = False

    def set_big_map(self, big_map: np.ndarray) -> None:
        """设置大地图.

        Args:
            big_map: 大地图图像数据
        """
        self.big_map = big_map

    def get_bw_map(
        self,
        local_screen: np.ndarray,
        scx: float,
        find_mode: int = 1,
    ) -> np.ndarray | None:
        """将小地图转换为黑白格式.

        提取小地图中的可移动区域(灰块)和边缘(白线).

        Args:
            local_screen: 小地图截图
            scx: 缩放系数
            find_mode: 寻路模式(0=录图,1=寻路)

        Returns:
            处理后的黑白地图,或 None 如果检测到祝福选择界面
        """
        shape = (int(scx * 190), int(scx * 190))

        # 创建空的黑白图
        bw_map = np.zeros(local_screen.shape[:2], dtype=np.uint8)

        # 检测灰块(可移动区域)
        gray_tolerance = 3200 + find_mode * 1600
        gray_mask = deepcopy(bw_map)
        gray_mask[
            np.sum((local_screen - self.COLOR_GRAY) ** 2, axis=-1) <= gray_tolerance
        ] = 255

        # 检测黑色区域
        black_tolerance = 800 + find_mode * 800
        black_mask = deepcopy(bw_map)
        black_mask[
            np.sum((local_screen - self.COLOR_BLACK) ** 2, axis=-1) <= black_tolerance
        ] = 255

        # 膨胀黑色区域
        kernel_large = np.ones((9, 9), np.uint8)
        cv.dilate(black_mask, kernel_large, iterations=1)

        # 膨胀灰块区域
        kernel_small = np.ones((5, 5), np.uint8)
        gray_mask = cv.dilate(gray_mask, kernel_small, iterations=1)

        # 检测白线(只保留灰块附近的白线)
        white_tolerance = 3200 + find_mode * 1600
        bw_map[
            (np.sum((local_screen - self.COLOR_WHITE) ** 2, axis=-1) <= white_tolerance)
            & (gray_mask > 200)
        ] = 255

        # 精确裁剪到标准尺寸
        if find_mode == 0:
            bw_map = bw_map[
                int(shape[0] * 0.5) - 68 : int(shape[0] * 0.5) + 108,
                int(shape[1] * 0.5) - 48 : int(shape[1] * 0.5) + 128,
            ]
        else:
            bw_map = bw_map[
                int(shape[0] * 0.5) - 68 - 2 : int(shape[0] * 0.5) + 108 - 2,
                int(shape[1] * 0.5) - 48 - 8 : int(shape[1] * 0.5) + 128 - 8,
            ]

        # 排除圆形区域外的像素
        center = 88
        radius = 85
        for i in range(bw_map.shape[0]):
            for j in range(bw_map.shape[1]):
                if (i - center) ** 2 + (j - center) ** 2 > radius ** 2:
                    bw_map[i, j] = 0

        return bw_map

    def get_loc(
        self,
        bw_map: np.ndarray,
        rg: int = 10,
        fbw: int = 0,
        offset: tuple[float, float] | None = None,
        find_mode: int = 1,
    ) -> None:
        """通过匹配获取当前位置.

        将小地图与大地图进行匹配,更新当前位置.

        Args:
            bw_map: 黑白格式的小地图
            rg: 搜索范围(以当前位置为中心)
            fbw: 是否进行缩放调整(0=静止状态,1=移动状态)
            offset: 位置偏移量 (dx, dy)
            find_mode: 寻路模式
        """
        if self.big_map is None:
            return

        rge = 88 + rg

        # 创建局部大地图副本
        loc_big = np.zeros((rge * 2, rge * 2), dtype=self.big_map.dtype)

        # 计算搜索中心点
        center = (self.now_loc[0], self.now_loc[1])
        if offset is not None:
            center = (center[0] + int(offset[0]), center[1] + int(offset[1]))

        # 计算裁剪边界
        x0 = max(rge - center[0], 0)
        y0 = max(rge - center[1], 0)
        x1 = max(center[0] + rge - self.big_map.shape[0], 0)
        y1 = max(center[1] + rge - self.big_map.shape[1], 0)

        # 从大地图中截取对应部分
        loc_big[x0 : rge * 2 - x1, y0 : rge * 2 - y1] = self.big_map[
            center[0] - rge + x0 : center[0] + rge - x1,
            center[1] - rge + y0 : center[1] + rge - y1,
        ]

        # 匹配搜索
        max_val, max_loc = -1, (0, 0)
        bo_1 = bw_map == 255
        kernel = np.ones((5, 5), np.uint8)

        # 缩放处理(移动状态调整)
        if find_mode and fbw == 0:
            tt = 4
            tbw = cv.resize(bw_map, (176 + tt * 2, 176 + tt * 2))
            tbw[tbw > 150] = 255
            tbw[tbw <= 150] = 0
            tbw = tbw[tt : 176 + tt, tt : 176 + tt]
            bo_2 = tbw == 255
            b_map = cv.dilate(tbw, kernel, iterations=1)
            bo_5 = (b_map != 0) & (bo_2 == 0)
        else:
            bo_2 = None
            bo_5 = None

        bo_3 = loc_big >= 50
        b_map = cv.dilate(bw_map, kernel, iterations=1)
        bo_4 = (b_map != 0) & (bo_1 == 0)

        # 枚举所有可能位置,找到最佳匹配
        for i in range(rge * 2 - 176):
            for j in range(rge * 2 - 176):
                # 只在搜索范围内查找
                if (i - rge + 88) ** 2 + (j - rge + 88) ** 2 > rg ** 2:
                    continue

                # 计算匹配分数
                p = 2 * np.count_nonzero(bo_3[i : i + 176, j : j + 176] & bo_1)
                p += np.count_nonzero(bo_3[i : i + 176, j : j + 176] & bo_4)

                if p > max_val:
                    max_val = p
                    max_loc = (i, j)

                # 缩放版本的匹配
                if find_mode and fbw == 0 and bo_2 is not None:
                    p = 2 * np.count_nonzero(bo_3[i : i + 176, j : j + 176] & bo_2)
                    p += np.count_nonzero(bo_3[i : i + 176, j : j + 176] & bo_5)
                    if p > max_val:
                        max_val = p
                        max_loc = (i, j)

        # 更新位置
        if max_val > 0:
            self.now_loc = (
                max_loc[0] + 88 - rge + self.now_loc[0],
                max_loc[1] + 88 - rge + self.now_loc[1],
            )

    def get_real_loc(self, delta: int = 0) -> None:
        """计算真实位置(考虑移动偏移).

        Args:
            delta: 移动增量系数
        """
        x, y = self.now_loc
        dx, dy = self.get_offset(delta=delta)
        self.real_loc = (int(x + 10 + dx), int(y + dy))

    def get_offset(self, delta: int = 1) -> tuple[float, float]:
        """根据视角角度计算位置偏移.

        Args:
            delta: 移动增量系数

        Returns:
            (dx, dy) 偏移量
        """
        if self.slow:
            delta = delta / 2

        pi = 3.141592653589
        dx = sin(self.ang / 180 * pi)
        dy = cos(self.ang / 180 * pi)
        return (delta * dx * 3, delta * dy * 3)

    @staticmethod
    def get_distance(point1: tuple, point2: tuple) -> float:
        """计算两点之间的距离.

        Args:
            point1: 第一个点 (x, y)
            point2: 第二个点 (x, y)

        Returns:
            两点之间的欧几里得距离
        """
        return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5

    def extract_features(self, img: np.ndarray) -> np.ndarray:
        """提取图像的 ORB 特征描述符.

        Args:
            img: 输入图像

        Returns:
            ORB 特征描述符
        """
        # 裁剪边缘
        img = img[50:-50, 50:-50, :]
        orb = cv.ORB_create()
        keypoints, descriptors = orb.detectAndCompute(img, None)
        return descriptors

    def match_map(
        self,
        img: np.ndarray,
        img_set: list,
        img_map: dict,
        scx: float,
    ) -> tuple[int, float]:
        """匹配地图,找到最相似的地图.

        Args:
            img: 当前小地图截图
            img_set: 地图特征集合 [(id, features), ...]
            img_map: 地图图像字典 {id: image, ...}
            scx: 缩放系数

        Returns:
            (地图ID, 相似度) 或 (-1, -1) 如果匹配失败
        """
        key = self.extract_features(img)
        bw_img = self.get_bw_map(img, scx, find_mode=0)

        matcher = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)
        results = []

        # 使用 ORB 特征进行初步筛选
        for map_id, features in img_set:
            try:
                matches = matcher.match(key, features)
                score = len(matches) / max(len(key), len(features))
                results.append((score, map_id))
            except:
                pass

        results = sorted(results, key=lambda x: x[0])[-3:]

        # 如果最高分明显高于次高分,直接返回
        try:
            if results[-1][0] > results[-2][0] + 0.065 and results[-1][0] > 0.4:
                return results[-1][1], 0.9
        except:
            return -1, -1

        # 使用模板匹配进行精确比对
        best_id, best_sim = -1, -1
        candidate_ids = [x[1] for x in results]

        for map_id in reversed(candidate_ids):
            bw_ref = self.get_bw_map(img_map[map_id], scx, find_mode=0)

            # 创建带边距的参考图
            padded_ref = np.zeros(
                (bw_ref.shape[0] + 28, bw_ref.shape[1] + 28),
                dtype=bw_ref.dtype,
            )
            padded_ref[14:-14, 14:-14] = bw_ref

            # 模板匹配
            result = cv.matchTemplate(padded_ref, bw_img, cv.TM_CCORR_NORMED)
            _, max_val, _, _ = cv.minMaxLoc(result)

            if max_val > best_sim:
                best_sim = max_val
                best_id = map_id

        return best_id, best_sim
