"""屏幕/图像基础操作(diver/simul 共享).

说明:
- 这里只放纯函数,避免依赖 UniverseUtils 具体实现.
- 目标是抽离 diver/simul 的 get_local 等重复逻辑.
"""

from __future__ import annotations

from typing import Tuple


def get_local(
    *,
    screen,
    window_width: int,
    window_height: int,
    x_ratio: float,
    y_ratio: float,
    size: Tuple[int, int],
    large: bool = True,
):
    """从截图中裁剪局部区域(以归一化坐标为中心).

    Args:
        screen: 当前截图(numpy.ndarray).
        window_width/window_height: 窗口宽高(像素).
        x_ratio/y_ratio: 归一化坐标(与 UniverseUtils.click 同一坐标系).
        size: (h, w) 目标区域大小(像素).
        large: 是否扩大裁剪范围(历史行为:额外 +60px).
    """

    sx = int(size[0] + 60 * int(bool(large)))
    sy = int(size[1] + 60 * int(bool(large)))

    bx = window_width - int(x_ratio * window_width)
    by = window_height - int(y_ratio * window_height)

    y0 = max(0, by - sx // 2)
    y1 = min(window_height, by + sx // 2)
    x0 = max(0, bx - sy // 2)
    x1 = min(window_width, bx + sy // 2)

    return screen[y0:y1, x0:x1, :]
