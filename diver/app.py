"""差分宇宙入口模块.

该文件负责启动编排.
"""

from __future__ import annotations

import traceback

from diver.universe import DivergentUniverse
from utils.log import log


def main() -> None:
    """差分宇宙主入口(供薄入口 run_diver.py 调用)."""

    universe = DivergentUniverse()

    try:
        universe.start()
    except Exception:
        # 兜底:入口层不吞错,打印堆栈,便于用户自行定位.
        log.error("启动差分宇宙时发生未捕获异常")
        traceback.print_exc()
        raise
