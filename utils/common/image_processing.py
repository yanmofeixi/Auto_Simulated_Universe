"""通用图像处理模块.

该模块提供游戏自动化中常用的图像处理函数,包括:
- 颜色掩码生成
- 形态学操作
- 黑白地图处理
- 特征提取和匹配

这些函数从 simul/utils.py 和 diver/utils.py 中提取,
避免重复代码并统一图像处理逻辑.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Tuple, Optional, List

import cv2 as cv
import numpy as np

from utils.common.constants import (
    Colors,
    ColorThresholds,
    HSVRanges,
    MinimapCoords,
    MorphologyKernels,
)

if TYPE_CHECKING:
    from numpy import ndarray


# ===== 颜色掩码函数 =====


def create_color_mask(
    image: ndarray,
    target_color: ndarray,
    threshold: float,
) -> ndarray:
    """创建颜色距离掩码.

    Args:
        image: 输入图像 (BGR 格式)
        target_color: 目标颜色 (BGR 格式)
        threshold: 颜色距离阈值

    Returns:
        二值掩码,匹配区域为 255,其他为 0
    """
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    color_dist = np.sum((image.astype(np.int32) - target_color) ** 2, axis=-1)
    mask[color_dist <= threshold] = 255
    return mask


# ===== 形态学操作 =====


def dilate(
    mask: ndarray,
    kernel_size: Tuple[int, int],
    iterations: int = 1,
) -> ndarray:
    """膨胀操作.

    Args:
        mask: 输入掩码
        kernel_size: 核大小 (height, width)
        iterations: 迭代次数

    Returns:
        膨胀后的掩码
    """
    kernel = np.ones(kernel_size, np.uint8)
    return cv.dilate(mask, kernel, iterations=iterations)


# ===== 小地图处理 =====


def crop_minimap(
    bw_map: ndarray,
    shape: Tuple[int, int],
    find_mode: int = 1,
) -> ndarray:
    """裁剪小地图到标准大小.

    Args:
        bw_map: 黑白小地图
        shape: 原始形状
        find_mode: 寻路模式

    Returns:
        裁剪后的小地图
    """
    if find_mode == 0:
        cropped = bw_map[
            int(shape[0] * 0.5) - MinimapCoords.CROP_OFFSET_Y_MIN : int(shape[0] * 0.5)
            + MinimapCoords.CROP_OFFSET_Y_MAX,
            int(shape[1] * 0.5) - MinimapCoords.CROP_OFFSET_X_MIN : int(shape[1] * 0.5)
            + MinimapCoords.CROP_OFFSET_X_MAX,
        ]
    else:
        cropped = bw_map[
            int(shape[0] * 0.5)
            - MinimapCoords.CROP_OFFSET_Y_MIN_FIND : int(shape[0] * 0.5)
            + MinimapCoords.CROP_OFFSET_Y_MAX_FIND,
            int(shape[1] * 0.5)
            - MinimapCoords.CROP_OFFSET_X_MIN_FIND : int(shape[1] * 0.5)
            + MinimapCoords.CROP_OFFSET_X_MAX_FIND,
        ]
    return cropped


def apply_circular_mask(
    bw_map: ndarray,
    center: Tuple[int, int] = (88, 88),
    radius: int = MinimapCoords.VALID_RADIUS_BW,
) -> ndarray:
    """应用圆形掩码,排除半径外的像素.

    Args:
        bw_map: 输入地图
        center: 圆心坐标
        radius: 有效半径

    Returns:
        应用掩码后的地图
    """
    result = bw_map.copy()
    for i in range(result.shape[0]):
        for j in range(result.shape[1]):
            if ((i - center[0]) ** 2 + (j - center[1]) ** 2) > radius**2:
                result[i, j] = 0
    return result


# ===== 终点检测 =====


def create_end_point_map(
    local_screen: ndarray,
    mask_value: int = 0,
    center: int = 660,
    mask_range: int = 350,
) -> ndarray:
    """创建终点检测用的黑白地图.

    Args:
        local_screen: 屏幕区域截图
        mask_value: 掩码值 (0 表示不使用掩码)
        center: 中心 X 坐标
        mask_range: 掩码范围

    Returns:
        用于终点匹配的黑白地图
    """
    bw_map = np.zeros(local_screen.shape[:2], dtype=np.uint8)

    # 黑色区域
    b_map = create_color_mask(
        local_screen, Colors.BLACK, ColorThresholds.END_POINT_BLACK
    )

    # 白色区域
    w_map = create_color_mask(
        local_screen, Colors.WHITE, ColorThresholds.END_POINT_WHITE
    )

    # 膨胀黑色区域
    b_map = dilate(b_map, MorphologyKernels.END_POINT_DILATE)

    # 黑白交界处
    bw_map[(b_map > 200) & (w_map > 200)] = 255

    # 应用掩码
    if mask_value:
        try:
            half_range = mask_range // mask_value
            bw_map[:, : center - half_range] = 0
            bw_map[:, center + half_range :] = 0
        except (ZeroDivisionError, IndexError):
            pass

    return bw_map


# ===== 自动战斗检测 =====


def check_auto_battle(
    screen_region: ndarray,
    min_count: int = 100,
    max_count: int = 280,
) -> bool:
    """检测是否开启自动战斗.

    Args:
        screen_region: 自动战斗指示器区域截图
        min_count: 最小像素计数
        max_count: 最大像素计数

    Returns:
        True 如果自动战斗已开启
    """
    hsv = cv.cvtColor(screen_region, cv.COLOR_BGR2HSV)
    mask = cv.inRange(hsv, HSVRanges.AUTO_BATTLE_LOWER, HSVRanges.AUTO_BATTLE_UPPER)
    count = np.sum(mask) // 255
    return min_count < count < max_count


def check_running_state(
    screen_region: ndarray,
    min_sum: int = 40000,
    max_sum: int = 65000,
) -> Tuple[bool, int]:
    """检测角色是否在跑步状态.

    Args:
        screen_region: 小地图中心区域截图
        min_sum: 最小掩码和
        max_sum: 最大掩码和

    Returns:
        (是否在跑步, 掩码像素和)
    """
    hsv = cv.cvtColor(screen_region, cv.COLOR_BGR2HSV)
    mask = cv.inRange(hsv, HSVRanges.RUNNING_LOWER, HSVRanges.RUNNING_UPPER)
    mask_sum = np.sum(mask)
    is_running = min_sum < mask_sum < max_sum
    return is_running, mask_sum


# ===== 特征匹配 =====


def extract_orb_features(
    image: ndarray,
    border: int = 50,
) -> Optional[ndarray]:
    """提取 ORB 特征描述符.

    Args:
        image: 输入图像
        border: 边界裁剪大小

    Returns:
        特征描述符,如果提取失败返回 None
    """
    if len(image.shape) == 3:
        cropped = image[border:-border, border:-border, :]
    else:
        cropped = image[border:-border, border:-border]

    orb = cv.ORB_create()
    keypoints, descriptors = orb.detectAndCompute(cropped, None)
    return descriptors


# ===== 距离计算 =====


def euclidean_distance(
    point1: Tuple[float, float],
    point2: Tuple[float, float],
) -> float:
    """计算两点间的欧几里得距离.

    Args:
        point1: 第一个点 (x, y)
        point2: 第二个点 (x, y)

    Returns:
        两点间的距离
    """
    return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5
