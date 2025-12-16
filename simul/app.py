"""普通模拟宇宙入口模块.

说明:
- run_simul.py 作为薄入口负责 UAC 提权与调用 main.
- 核心逻辑位于 simul/universe_core.py(SimulatedUniverse),simul/universe.py 仅做导出.

注意:
- 该文件只做参数解析/配置注入/启动编排,避免再次演化为巨型脚本.
"""

from __future__ import annotations

import traceback
from typing import List, Optional

from utils.log import log
from simul.args import parse_args
from simul.config import config
from simul.universe import SimulatedUniverse


def main(argv: Optional[List[str]] = None) -> None:
    """普通模拟宇宙主入口(供薄入口 run_simul.py 调用)."""

    parsed_args = parse_args(argv)

    # 兼容旧行为:未显式传入的选项,从配置文件读取默认值.
    speed = config.speed_mode if parsed_args.speed is None else int(parsed_args.speed)
    consumable = (
        config.use_consumable if parsed_args.consumable is None else int(parsed_args.consumable)
    )
    slow = config.slow_mode if parsed_args.slow is None else int(parsed_args.slow)
    bonus = bool(config.bonus) if parsed_args.bonus is None else bool(int(parsed_args.bonus))

    find = int(parsed_args.find)
    debug = int(parsed_args.debug)
    show_map = int(parsed_args.show_map)
    update = int(parsed_args.update)
    unlock = bool(parsed_args.unlock)

    log.info(
        f"find: {find}, debug: {debug}, show_map: {show_map}, consumable: {consumable}"
    )

    universe = SimulatedUniverse(
        find,
        debug,
        show_map,
        speed,
        consumable,
        slow,
        unlock=unlock,
        bonus=bonus,
        update=update,
    )

    try:
        universe.start()
    except Exception:
        traceback.print_exc()
        raise
