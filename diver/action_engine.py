from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Union

from utils.log import log


JsonAction = Dict[str, Any]
JsonActionFile = DefaultDict[str, List[JsonAction]]


@dataclass(frozen=True)
class StaticRunResult:
    """静态规则命中结果."""

    name: str


class ActionEngine:
    """基于 OCR + 规则 JSON 的静态动作执行器."""

    def __init__(self, ctx: Any):
        self._ctx = ctx

    def load_actions(self, json_path: str) -> JsonActionFile:
        res: JsonActionFile = defaultdict(list)
        with open(json_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                res[item["name"]].append(item)
        return res

    def do_action(self, action: Union[str, JsonAction]) -> int:
        """执行单条动作.

        action 支持:
        - str:调用 ctx 上同名方法
        - dict:支持 text/position/sleep/press 等动作
        """

        if isinstance(action, str):
            result = getattr(self._ctx, action)()
            return int(result) if result is not None else 1

        if "text" in action:
            box = action.get("box", [0, 1920, 0, 1080])
            text = self._ctx.ts.find_with_box(
                box, redundancy=action.get("redundancy", 30)
            )
            for item in text:
                if action["text"] in item["raw_text"]:
                    log.info(f"点击 {action['text']}:{item['box']}")
                    self._ctx.click_box(item["box"])
                    return 1
            return 0

        if "position" in action:
            log.info(f"点击 {action['position']}")
            self._ctx.click_position(action["position"])
            return 1

        if "sleep" in action:
            self._ctx.sleep(float(action["sleep"]))
            return 1

        if "press" in action:
            self._ctx.press(action["press"], action.get("time", 0))
            return 1

        return 0

    def run_static(
        self,
        *,
        json_file: Optional[JsonActionFile] = None,
        json_path: Optional[str] = None,
        action_list: Optional[Iterable[str]] = None,
        skip_check: int = 0,
        merge_text_fn: Optional[Any] = None,
    ) -> str:
        """执行静态规则.

        返回命中的规则 name;未命中返回空字符串.
        """

        if merge_text_fn is None:
            merge_text_fn = getattr(self._ctx, "merge_text")

        if json_file is None:
            if json_path is None:
                json_file = self._ctx.default_json
            else:
                json_file = self.load_actions(json_path)

        names = list(action_list) if action_list else list(json_file.keys())

        for name in names:
            for rule in json_file[name]:
                trigger = rule["trigger"]
                text = self._ctx.ts.find_with_box(
                    trigger["box"],
                    redundancy=trigger.get("redundancy", 30),
                )
                if skip_check or (len(text) and trigger["text"] in merge_text_fn(text)):
                    log.info(f"触发 {rule['name']}:{trigger['text']}")
                    for act in rule["actions"]:
                        self.do_action(act)
                    return str(rule["name"])

        return ""
