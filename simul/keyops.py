"""普通模拟宇宙:按键操作封装."""

from __future__ import annotations

from utils.common.keyops import get_mapping as _get_mapping
from utils.common.keyops import key_down as _key_down
from utils.common.keyops import key_up as _key_up
from simul.config import config


def get_mapping(key: str) -> str:
    """将逻辑按键映射为实际按键."""

    return _get_mapping(key, origin_key=config.origin_key, mapping=config.mapping)


def keyDown(key: str) -> None:
    """按下按键(带映射)."""

    _key_down(key, origin_key=config.origin_key, mapping=config.mapping)


def keyUp(key: str) -> None:
    """松开按键(带映射)."""

    _key_up(
        key,
        origin_key=config.origin_key,
        mapping=config.mapping,
    )
