"""差分宇宙:通用弹窗/遮挡层处理器."""

from __future__ import annotations

import time

from typing import Iterable, Optional


def check_pop(
    universe,
    *,
    timeout_s: float = 3.0,
    poll_interval_s: float = 0.5,
    action_list: Optional[Iterable[str]] = None,
    after_action_sleep_s: float = 0.3,
) -> None:
    """关闭可能弹出的遮挡窗口(例如“点击空白处关闭”)."""

    if action_list is None:
        action_list = ["点击空白处关闭"]

    start_time = time.time()
    while True:
        time.sleep(poll_interval_s)
        universe.ts.forward(universe.get_screen())
        if universe.get_now_area() is not None:
            break
        if universe.run_static(action_list=list(action_list)):
            time.sleep(after_action_sleep_s)
        elif time.time() - start_time > timeout_s:
            break
