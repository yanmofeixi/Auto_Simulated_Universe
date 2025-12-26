"""通用 UI 输入操作模块."""

from __future__ import annotations

import time

from typing import Callable, Protocol


class _KeyOps(Protocol):
    """按键操作协议."""

    def keyDown(self, key: str) -> None: ...

    def keyUp(self, key: str) -> None: ...


def gen_hotkey_img(*, hotkey: str = "e", bg: str = "imgs/f_bg.jpg"):
    """生成热键提示图片."""

    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    hotkey_text = hotkey.upper()
    image = Image.open(bg)
    font = ImageFont.truetype("imgs/base.ttf", 24)
    drawer = ImageDraw.Draw(image)
    position = (2, -3)
    color = (152, 214, 241)
    drawer.text(position, hotkey_text, font=font, fill=color)
    return np.array(image)


def press_key(
    *,
    key: str,
    duration: float = 0,
    log,
    keyops: _KeyOps,
    allow_e: bool,
    stop_flag: Callable[[], int],
) -> None:
    """按下并释放按键.

    语义保持与历史实现一致:
    - 若 key 不在 "3r" 中,会输出 debug 日志
    - 若 key == 'e' 且 allow_e 为 False,则直接返回
    - 若 stop_flag() != 0,抛出 ValueError("正在退出")
    """

    if key not in "3r":
        log.debug(f"按下按钮 {key},等待 {duration} 秒后释放")

    if key == "e" and not allow_e:
        return

    if stop_flag() == 0:
        keyops.keyDown(key)
    else:
        raise ValueError("正在退出")

    time.sleep(duration)
    keyops.keyUp(key)


def sprint(
    *,
    log,
    keyops: _KeyOps,
    press: Callable[[str, float], None],
) -> None:
    """冲刺(shift)."""

    press("shift", 0)


def wait_fig(
    *,
    predicate: Callable[[], bool],
    timeout: float = 3,
    get_screen: Callable[[], object],
) -> int:
    """等待某个条件变为 False.

    与历史实现保持一致:
    - predicate() 返回 True 代表“继续等待”
    - predicate() 返回 False 代表“条件已满足”,立刻返回 1
    - 超时返回 0

    注意:过程中会周期性调用 get_screen() 刷新画面.
    """

    start_time = time.time()
    while time.time() - start_time < timeout:
        if not predicate():
            return 1
        time.sleep(0.1)
        get_screen()
    return 0


def calc_point(
    *,
    point: tuple[float, float],
    offset: tuple[float, float],
    window_width: int,
    window_height: int,
) -> tuple[float, float]:
    """把像素偏移量换算成归一化坐标的偏移并应用.

    历史语义:
    - point: (x_ratio, y_ratio)
    - offset: (dx_px, dy_px)
    - 返回:修正后的 (x_ratio, y_ratio)
    """

    return (
        point[0] - offset[0] / window_width,
        point[1] - offset[1] / window_height,
    )


def click_box(
    *,
    box: list[float] | tuple[float, float, float, float],
    window_width: int,
    window_height: int,
    click: Callable[[tuple[float, float]], None],
) -> None:
    """点击一个 box 的中心点.

    box: (x_min, x_max, y_min, y_max),单位为像素.
    click: 上层提供的点击函数(通常是 UniverseUtils.click).
    """

    center_x = (box[0] + box[1]) / 2
    center_y = (box[2] + box[3]) / 2
    click((1 - center_x / window_width, 1 - center_y / window_height))


def click_position(
    *,
    position: tuple[float, float],
    window_width: int,
    window_height: int,
    click: Callable[[tuple[float, float]], None],
) -> None:
    """点击一个像素坐标位置(position=(x,y))."""

    click_box(
        box=[position[0], position[0], position[1], position[1]],
        window_width=window_width,
        window_height=window_height,
        click=click,
    )


def click(
    *,
    points: tuple[object, object],
    click_enabled: bool = True,
    debug_level: int = 0,
    print_func=print,
    print_stack: Callable[[], None] | None = None,
    x1: int,
    y1: int,
    window_width: int,
    window_height: int,
    is_fullscreen: bool,
    fullscreen_offset_px: int = 9,
    stop_flag: Callable[[], int],
    post_delay_s: float = 0.3,
) -> None:
    """点击一个点(像素坐标或归一化坐标).

    与 diver/simul 现有实现保持一致:
    - debug_level == 2 时打印 points
    - 调用 print_stack()(如果提供)
    - points 若为归一化坐标 (float, float) 则按窗口换算成像素坐标
    - 全屏模式额外 +9 像素偏移
    - stop_flag() != 0 时抛出 ValueError("正在退出")
    """

    if debug_level == 2:
        print_func(points)

    if print_stack is not None:
        print_stack()

    x, y = points

    # 如果是归一化坐标(float 等),则计算实际像素坐标
    # 使用 Integral 覆盖 int/numpy.int 等,避免与两侧原实现的 type 判断产生差异
    from numbers import Integral

    if not (isinstance(x, Integral) and isinstance(y, Integral)):
        x = x1 - int(float(x) * window_width)
        y = y1 - int(float(y) * window_height)
    else:
        x = int(x)
        y = int(y)

    if is_fullscreen:
        x += fullscreen_offset_px
        y += fullscreen_offset_px

    if stop_flag() != 0:
        raise ValueError("正在退出")

    import pyautogui

    # 延迟导入:减少模块级副作用
    import win32api

    win32api.SetCursorPos((x, y))
    if click_enabled:
        pyautogui.click()

    time.sleep(post_delay_s)
