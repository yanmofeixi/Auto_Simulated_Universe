"""游戏自动化通用常量模块.

该模块集中管理游戏自动化中使用的各种常量,包括:
- 颜色阈值 (用于图像处理)
- 坐标比例 (用于小地图和UI定位)
- HSV 颜色范围 (用于掩码生成)
- 默认阈值和超时时间

将这些常量集中管理可以:
1. 避免魔法数字散布在代码各处
2. 便于统一调整和维护
3. 提高代码可读性
"""

from __future__ import annotations

import numpy as np
from typing import Tuple

# ===== 基础颜色 (BGR 格式) =====


class Colors:
    """常用颜色常量 (BGR 格式)."""

    BLACK = np.array([0, 0, 0])
    WHITE = np.array([255, 255, 255])
    GRAY = np.array([55, 55, 55])
    WHITE_210 = np.array([210, 210, 210])
    YELLOW = np.array([145, 192, 220])
    BLUE = np.array([234, 191, 4])
    SRED = np.array([49, 49, 140])
    RED_MINIMAP = np.array([60, 60, 226])


# ===== 颜色距离阈值 =====


class ColorThresholds:
    """颜色匹配的距离阈值.

    用于判断像素是否匹配目标颜色,计算方式为:
    np.sum((pixel - target_color) ** 2) <= threshold
    """

    # 终点检测中的黑白检测
    END_POINT_BLACK = 1600
    END_POINT_WHITE = 1600

    # 小地图中的灰块检测
    MINIMAP_GRAY_BASE = 3200
    MINIMAP_GRAY_FIND_BONUS = 1600

    # 小地图中的黑色检测
    MINIMAP_BLACK_BASE = 800
    MINIMAP_BLACK_FIND_BONUS = 800

    # 小地图中的白线检测
    MINIMAP_WHITE_BASE = 3200
    MINIMAP_WHITE_FIND_BONUS = 1600

    # 红色点检测 (怪物/传送点)
    MINIMAP_RED = 512


# ===== HSV 颜色范围 =====


class HSVRanges:
    """HSV 颜色范围,用于 cv.inRange 掩码生成."""

    # 自动战斗检测 (黄色指示器)
    AUTO_BATTLE_LOWER = np.array([22, 58, 100])
    AUTO_BATTLE_UPPER = np.array([26, 100, 255])

    # 运行状态检测 (蓝色箭头)
    RUNNING_LOWER = np.array([93, 120, 60])
    RUNNING_UPPER = np.array([97, 255, 255])


# ===== 小地图相关坐标 =====


class MinimapCoords:
    """小地图相关的坐标常量."""

    # 小地图中心相对于屏幕的比例位置 (从右下角计算)
    CENTER_X_RATIO = 0.9333
    CENTER_Y_RATIO = 0.8657

    # 小地图当前位置偏移
    CURRENT_LOC_OFFSET = (118 + 2, 125 + 2)

    # 小地图有效半径
    VALID_RADIUS = 82
    VALID_RADIUS_BW = 85
    VALID_RADIUS_WRITE = 80

    # 小地图裁剪偏移 (find=0 模式)
    CROP_OFFSET_Y_MIN = 68
    CROP_OFFSET_Y_MAX = 108
    CROP_OFFSET_X_MIN = 48
    CROP_OFFSET_X_MAX = 128

    # 小地图裁剪偏移 (find=1 模式)
    CROP_OFFSET_Y_MIN_FIND = 68 + 2
    CROP_OFFSET_Y_MAX_FIND = 108 - 2
    CROP_OFFSET_X_MIN_FIND = 48 + 8
    CROP_OFFSET_X_MAX_FIND = 128 - 8


# ===== UI 坐标 =====


class UICoords:
    """UI 元素的坐标比例.

    坐标使用相对比例表示,从右下角开始计算:
    实际坐标 = (1 - ratio) * 窗口尺寸
    """

    # F 键交互提示
    F_KEY_X = 0.4443
    F_KEY_Y = 0.4417

    # 选择祝福界面
    CHOOSE_BLESSING_X = 0.9266
    CHOOSE_BLESSING_Y = 0.9491

    # 重置按钮
    RESET_X = 0.2938
    RESET_Y = 0.0954

    # 自动战斗指示器
    AUTO_BATTLE_X = 0.0878
    AUTO_BATTLE_Y = 0.9630

    # 运行状态检测
    RUN_X = 0.876
    RUN_Y = 0.7815

    # 终点检测区域
    END_POINT_X = 0.4979
    END_POINT_Y = 0.6296
    END_POINT_SIZE = (715, 1399)
    END_POINT_CENTER = 660


# ===== 匹配阈值 =====


class MatchThresholds:
    """模板匹配的阈值常量."""

    # 默认匹配阈值
    DEFAULT = 0.95

    # F 键检测阈值
    F_KEY = 0.96

    # 交互点检测阈值
    INTERACTION = 0.88

    # 运行状态检测阈值
    RUNNING = 0.91

    # 终点检测阈值
    END_POINT = 0.6

    # 地图匹配阈值
    MAP_MATCH = 0.4


# ===== 鼠标移动参数 =====


class MouseParams:
    """鼠标移动相关参数."""

    # 单次移动最大角度
    MAX_ANGLE_PER_MOVE = 30

    # 角度到像素的转换系数
    ANGLE_TO_PIXEL = 16.5

    # 移动后等待时间 (秒)
    MOVE_DELAY = 0.05


# ===== 形态学操作核大小 =====


class MorphologyKernels:
    """形态学操作的核大小."""

    # 终点检测膨胀核
    END_POINT_DILATE = (7, 7)

    # 小地图黑色区域膨胀核
    MINIMAP_BLACK_DILATE = (9, 9)

    # 小地图灰色区域膨胀核
    MINIMAP_GRAY_DILATE = (5, 5)

    # 地图匹配膨胀核
    MAP_MATCH_DILATE = (5, 5)


# ===== 目标点距离阈值 =====


class TargetDistances:
    """到达目标点的距离阈值."""

    # 不同类型目标的到达距离 [type_0, type_1, type_2, type_3]
    # type_0: 普通路点, type_1: 交互点, type_2: 黑塔, type_3: 传送点
    BASE_DISTANCES = [13, 9, 11, 7]

    # 黄泉模式的额外距离
    QUAN_BONUS = 7

    # 移除目标点的距离
    REMOVE_DISTANCE = 20


# ===== 时间常量 =====


class Timeouts:
    """超时和延迟常量 (秒)."""

    # 等待图像出现的默认超时
    WAIT_FIG_DEFAULT = 3.0

    # 窗口等待间隔
    WINDOW_POLL_INTERVAL = 0.5

    # 按键后延迟
    KEY_PRESS_DELAY = 0.1

    # 点击后延迟
    CLICK_DELAY = 0.5

    # 交互确认超时
    INTERACTION_CONFIRM = 1.6

    # 地图切换等待时间
    MAP_TRANSITION = 1.5
