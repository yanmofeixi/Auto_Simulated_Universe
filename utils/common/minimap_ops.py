"""小地图相关操作(diver/simul 共享).

抽离点:
- exist_minimap:裁剪并强化蓝色箭头
- get_now_direc:通过旋转模板匹配求当前角度
- take_fine_minimap:通过上下抖动视角生成“细化小地图”

注意:
- get_bw_map 依赖大量上层状态(find/check/map_file/debug),本次先不强行抽掉,
  以免参数爆炸;后续可以再二次抽离.
"""

from __future__ import annotations

import time

from typing import Callable, Tuple


def exist_minimap(
    *,
    get_screen: Callable[[], object],
    get_local: Callable[[float, float, Tuple[int, int], bool], object],
    scx: float,
):
    """裁剪小地图并增强箭头蓝色,返回增强后的局部截图."""

    screen = get_screen()
    shape = (int(scx * 190), int(scx * 190))
    local_screen = get_local(0.9333, 0.8657, shape, True)

    import numpy as np

    blue = np.array([234, 191, 4])
    local_screen[np.sum(np.abs(local_screen - blue), axis=-1) <= 50] = blue
    return local_screen


def handle_rotate_val(x: int, y: int, rotate: float):
    """计算旋转变换矩阵."""

    import numpy as np

    cos_val = np.cos(np.deg2rad(rotate))
    sin_val = np.sin(np.deg2rad(rotate))
    return np.float32(
        [
            [cos_val, sin_val, x * (1 - cos_val) - y * sin_val],
            [-sin_val, cos_val, x * sin_val + y * (1 - cos_val)],
        ]
    )


def image_rotate(src, rotate: float = 0):
    """图像旋转(以中心点为轴)."""

    import cv2 as cv

    h, w, _c = src.shape
    matrix = handle_rotate_val(w // 2, h // 2, rotate)
    return cv.warpAffine(src, matrix, (w, h))


def get_now_direc(*, cv, loc_scr, arrow_template_path: str):
    """计算小地图中蓝色箭头的角度."""

    import numpy as np

    arrow = cv.imread(arrow_template_path)
    hsv = cv.cvtColor(loc_scr, cv.COLOR_BGR2HSV)
    lower = np.array([93, 90, 60])
    upper = np.array([97, 255, 255])
    mask = cv.inRange(hsv, lower, upper)
    loc_tp = cv.bitwise_and(loc_scr, loc_scr, mask=mask)

    mx_acc = 0.0
    ang = 0
    for i in range(360):
        rt = image_rotate(arrow, i)
        result = cv.matchTemplate(loc_tp, rt, cv.TM_CCORR_NORMED)
        _min_val, max_val, _min_loc, _max_loc = cv.minMaxLoc(result)
        if max_val > mx_acc:
            mx_acc = float(max_val)
            ang = int(i)
    return ang


def take_fine_minimap(
    *,
    get_screen: Callable[[], object],
    exist_minimap_fn: Callable[[], object],
    n: int = 5,
    dt: float = 0.01,
    dy: int = 200,
    out_img_path: str = "imgs/fine_minimap.jpg",
    out_mask_path: str = "imgs/fine_mask.jpg",
):
    """移动视角并生成小地图中不变部分(白线/灰块)的细化图."""

    from copy import deepcopy

    import cv2 as cv
    import numpy as np
    import win32api
    import win32con

    get_screen()
    local_scr = exist_minimap_fn()

    total_img = local_scr
    total_mask = 255 * np.array(total_img.shape)

    n = 4
    for _ in range(n):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, -dy, 0, 0)
        get_screen()
        local_scr = exist_minimap_fn()
        mask = cv.compare(total_img, local_scr, cv.CMP_EQ)
        total_mask = cv.bitwise_and(total_mask, mask)
        total_img = cv.bitwise_and(total_mask, total_img)
        time.sleep(dt)

    time.sleep(0.1)

    for _ in range(n // 2):
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 2 * dy, 0, 0)
        get_screen()
        local_scr = exist_minimap_fn()
        mask = cv.compare(total_img, local_scr, cv.CMP_EQ)
        total_mask = cv.bitwise_and(total_mask, mask)
        total_img = cv.bitwise_and(total_mask, total_img)
        time.sleep(dt)

    cv.imwrite(out_img_path, total_img)
    cv.imwrite(out_mask_path, total_mask)
    return total_img, total_mask
