"""差分宇宙:按键操作封装."""

from __future__ import annotations

from utils.common.keyops import KeyController as _KeyController
from utils.common.keyops import key_down as keyDown
from utils.common.keyops import key_up as keyUp

__all__ = ["keyDown", "keyUp", "KeyController"]


class KeyController(_KeyController):
    """差分宇宙按键控制器,封装按键操作."""

    def __init__(self, father):
        super().__init__(father, key_down_fn=keyDown, key_up_fn=keyUp)
