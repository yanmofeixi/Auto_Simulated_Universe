"""普通模拟宇宙自动化:对外 API 壳.

该模块仅用于导出核心类,避免实现文件过大导致导入成本上升.
"""

from __future__ import annotations

from simul.universe_core import SimulatedUniverse, version

__all__ = ["SimulatedUniverse", "version"]
