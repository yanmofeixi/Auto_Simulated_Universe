"""按键操作封装(可复用).

该模块提供:
- 逻辑按键到实际按键的映射
- keyDown/keyUp 的公共实现
- 可选的 KeyController(用于自动重复按键/队列事件)

diver/simul 可通过薄壳传入各自 config 来复用.
"""

from __future__ import annotations

import threading
import time
from typing import Callable, List, Sequence

import pyautogui


def get_mapping(key: str, *, origin_key: Sequence[str], mapping: Sequence[str]) -> str:
    """将逻辑按键映射为实际按键."""

    try:
        index = list(origin_key).index(key)
    except ValueError:
        return key
    except Exception:
        return key

    try:
        return mapping[index]
    except Exception:
        return key


def key_down(
    key: str,
    *,
    origin_key: Sequence[str],
    mapping: Sequence[str],
) -> None:
    """按下按键(带映射)."""

    pyautogui.keyDown(get_mapping(key, origin_key=origin_key, mapping=mapping))


def key_up(
    key: str,
    *,
    origin_key: Sequence[str],
    mapping: Sequence[str],
) -> None:
    """松开按键(带映射)."""

    pyautogui.keyUp(get_mapping(key, origin_key=origin_key, mapping=mapping))


class KeyController:
    """按键事件控制器(可选)."""

    def __init__(
        self,
        father,
        *,
        key_down_fn: Callable[[str], None],
        key_up_fn: Callable[[str], None],
    ):
        self.events: List[dict] = []
        self.fff = 0
        self.father = father
        self._lock = threading.Lock()
        self._key_down = key_down_fn
        self._key_up = key_up_fn
        self._thread = threading.Thread(target=self.loop, daemon=True)
        self._thread.start()

    def add_event(self, event_type: str, key: str) -> None:
        """追加一个按键事件."""

        with self._lock:
            self.events.append({"type": event_type, "key": key})

    def clear_events(self) -> None:
        """清空事件队列."""

        with self._lock:
            self.events.clear()

    def loop(self) -> None:
        """后台循环:持续处理 fff 连发和事件队列."""

        while not getattr(self.father, "_stop", True):
            if self.fff:
                self._key_down("f")
                time.sleep(0.02)
                self._key_up("f")
            else:
                time.sleep(0.1)

            with self._lock:
                events_snapshot = list(self.events)

            for event in events_snapshot:
                if event.get("type") == "down":
                    self._key_down(event.get("key", ""))
                elif event.get("type") == "up":
                    self._key_up(event.get("key", ""))
