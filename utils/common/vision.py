"""通用图像/模板匹配工具(diver/simul 共享).

当前阶段采取“最小抽离”策略:
- 先抽 diver/simul 中实现完全一致、且不依赖 UniverseUtils 状态的函数.
- 后续再逐步抽 click_target/check_box/get_local 等更高层逻辑.

注意:
- 这些函数依赖 pyautogui / numpy / opencv-python.
- 为减少模块级导入副作用,这里使用延迟导入.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


def scan_screenshot(prepared) -> Dict[str, Any]:
    """截取全屏并进行模板匹配.

    参数:
    - prepared: 模板图(通常为 cv.imread() 的结果)

    返回:与历史实现保持一致的 dict:
    - screenshot: RGB 格式截图(numpy.ndarray)
    - min_val/max_val/min_loc/max_loc: cv.minMaxLoc 的输出
    """

    import cv2 as cv
    import numpy as np
    import pyautogui

    temp = pyautogui.screenshot()
    screenshot = np.array(temp)
    screenshot = cv.cvtColor(screenshot, cv.COLOR_BGR2RGB)
    result = cv.matchTemplate(screenshot, prepared, cv.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(result)
    return {
        "screenshot": screenshot,
        "min_val": min_val,
        "max_val": max_val,
        "min_loc": min_loc,
        "max_loc": max_loc,
    }


def calculated(result: Dict[str, Any], shape: Tuple[int, int, int]) -> Tuple[int, int]:
    """计算匹配中心点坐标(像素).

    参数:
    - result: scan_screenshot 返回的 dict(至少包含 max_loc)
    - shape: 模板的 shape(通常是 prepared.shape)

    返回:
    - (x, y) 像素坐标
    """

    mat_top, mat_left = result["max_loc"]
    prepared_height, prepared_width, _prepared_channels = shape
    x = int((mat_top + mat_top + prepared_width) / 2)
    y = int((mat_left + mat_left + prepared_height) / 2)
    return x, y


def click_target(
    *,
    target_path: str,
    threshold: float,
    must_match: bool = True,
    print_func=print,
    on_found=None,
    exit_on_found: bool = False,
) -> Tuple[int, int] | None:
    """寻找并定位模板匹配点.

    参数:
    - target_path: 模板路径
    - threshold: 匹配阈值
    - must_match: True 表示必须匹配(会一直循环直到匹配到);False 则不匹配直接返回 None
    - print_func: 输出函数
    - on_found: 匹配成功后的回调,签名为 on_found(points, result, template)
    - exit_on_found: 匹配到后直接退出进程

    返回:
    - 成功:匹配中心点 (x, y)
    - 失败(must_match=False 且未匹配到):None
    """

    import cv2 as cv

    template = cv.imread(target_path)
    if template is None:
        # 保持“静默失败”风格:无法读取模板时直接视作找不到
        return None

    while True:
        result = scan_screenshot(template)
        if result["max_val"] > threshold:
            print_func(result["max_val"])
            points = calculated(result, template.shape)

            if on_found is not None:
                try:
                    on_found(points, result, template)
                except Exception:
                    # click_target 主要用于调试,不让回调异常影响主流程
                    pass

            if exit_on_found:
                raise SystemExit(0)

            return points

        if not must_match:
            return None
