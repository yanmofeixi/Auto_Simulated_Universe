"""模板匹配(diver/simul 共享).

抽离点:
- diver/simul 的 UniverseUtils.check() 逻辑几乎一致
- 差异主要在:路径前缀,少量 debug 写文件,以及调用方如何存储 tx/ty/tm

本模块提供纯函数:
- 只负责读取模板,按 scx 缩放,裁剪局部区域并做 matchTemplate
- 返回 (max_val, tx, ty, local_screen)

调用方(diver/simul)再决定:
- 是否记录日志
- 是否更新 self.last_info/self.tm/self.tx/self.ty
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple


@dataclass(frozen=True)
class TemplateMatchResult:
    matched: bool
    max_val: float
    tx: float
    ty: float
    local_screen: Any


def match_template_near_point(
    *,
    cv,
    screen: Any,
    read_image: Callable[[str], Any],
    format_path: Callable[[str], str],
    get_local: Callable[[float, float, Tuple[int, int], bool], Any],
    path: str,
    x_ratio: float,
    y_ratio: float,
    scx: float,
    threshold: float,
    mask: Optional[str] = None,
    large: bool = True,
    target_image: Optional[Any] = None,
) -> TemplateMatchResult:
    """在指定归一化坐标附近做模板匹配."""

    target = target_image
    if target is None:
        target_path = format_path(path)
        target = read_image(target_path)

    if target is None:
        return TemplateMatchResult(False, 0.0, x_ratio, y_ratio, None)

    target = cv.resize(
        target,
        dsize=(int(scx * target.shape[1]), int(scx * target.shape[0])),
    )

    if mask is None:
        shape = target.shape
    else:
        mask_img = read_image(format_path(mask))
        shape = (
            int(scx * mask_img.shape[0]),
            int(scx * mask_img.shape[1]),
        )

    local_screen = get_local(x_ratio, y_ratio, shape, large)
    if large is False:
        # 历史行为:large=False 直接返回局部截图
        return TemplateMatchResult(False, 0.0, x_ratio, y_ratio, local_screen)

    result = cv.matchTemplate(local_screen, target, cv.TM_CCORR_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv.minMaxLoc(result)

    # tx/ty:匹配中心点的归一化坐标(与历史实现一致)
    tx = x_ratio - (
        max_loc[0]
        - 0.5 * local_screen.shape[1]
        + 0.5 * target.shape[1]
    ) / screen.shape[1]
    ty = y_ratio - (
        max_loc[1]
        - 0.5 * local_screen.shape[0]
        + 0.5 * target.shape[0]
    ) / screen.shape[0]

    return TemplateMatchResult(bool(max_val > threshold), float(max_val), float(tx), float(ty), local_screen)
