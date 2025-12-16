"""差分宇宙:按键操作封装."""

from __future__ import annotations

from typing import List

from diver.config import config

from utils.common.keyops import KeyController as _KeyController
from utils.common.keyops import get_mapping as _get_mapping
from utils.common.keyops import key_down as _key_down
from utils.common.keyops import key_up as _key_up

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

class KeyController(_KeyController):
    """差分宇宙按键控制器,封装按键操作."""

    def __init__(self, father):
        super().__init__(father, key_down_fn=keyDown, key_up_fn=keyUp)
