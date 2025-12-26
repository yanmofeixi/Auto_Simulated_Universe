"""小地图相关操作(diver/simul 共享).

抽离点:
- exist_minimap:裁剪并强化蓝色箭头
- get_now_direc:通过旋转模板匹配求当前角度

注意:
- get_bw_map 依赖大量上层状态(find/check/map_file/debug),本次先不强行抽掉,
  以免参数爆炸;后续可以再二次抽离.
"""

from __future__ import annotations

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
