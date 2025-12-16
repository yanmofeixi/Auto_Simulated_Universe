"""simul 侧地图日志:兼容导出.

历史路径:utils/simul/map_log.py
当前实现:复用 utils/common/map_log.py,避免 diver/simul 重复维护.
"""

from __future__ import annotations

from utils.common.map_log import map_log

__all__ = ["map_log"]
