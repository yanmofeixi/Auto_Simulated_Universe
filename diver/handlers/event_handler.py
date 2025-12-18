"""差分宇宙:事件处理器.

该模块只负责“事件界面”的识别与交互流程:
- 识别当前事件标题
- 在事件选项中按规则打分并选择
- 对齐事件交互点(align_event)
"""

from __future__ import annotations

import time
from typing import Optional

import pyautogui

from utils.log import log
from utils.log import my_print as print
from diver.handlers.popup_handler import check_pop


def _resolve_event_key(universe, title_text: str, current_event_key: Optional[str]) -> tuple[Optional[str], int]:
    """根据标题文本解析事件 key.

    返回:
    - event_key:事件名(未解析则为 None)
    - start_flag:保持原逻辑语义(仅在首次解析时根据 universe.now_event 判定)
    """

    if current_event_key is not None:
        return current_event_key, 0

    best_key: Optional[str] = None
    for candidate_key in universe.event_prior:
        if candidate_key in title_text and (best_key is None or len(candidate_key) > len(best_key)):
            best_key = candidate_key

    start = int(best_key is not None and universe.now_event == best_key)
    if best_key is not None:
        universe.now_event = best_key
        log.info(f"event:{best_key},start:{bool(start)}")
    return best_key, start


def _is_in_event_page(universe) -> bool:
    """判断当前是否仍在事件界面."""

    return "事件" in universe.merge_text(universe.ts.find_with_box([92, 195, 54, 88]))


def _parse_event_choices(universe) -> list[dict]:
    """解析事件选项列表为结构化数据."""

    text = universe.ts.find_with_box([1300, 1920, 100, 1080], redundancy=30)

    events: list[dict] = []
    event_now: Optional[dict] = None
    last_star = 0

    for item in text:
        if (
            universe.check_box(
                "star",
                [1250, 1460, item["box"][2] - 30, item["box"][3] + 30],
            )
            and last_star < universe.ty - 20
        ):
            last_star = universe.ty
            if event_now is not None:
                events.append(event_now)
            event_now = {"raw_text": item["raw_text"].lstrip("米"), "box": item["box"]}
        else:
            if event_now is not None:
                event_now["raw_text"] += item["raw_text"]
            else:
                event_now = {"raw_text": item["raw_text"], "box": item["box"]}

    if event_now is not None:
        events.append(event_now)

    for event in events:
        event["raw_text"] = universe.clean_text(event["raw_text"], 0)

    return events


def _score_event_choices(universe, choices: list[dict], event_key: str) -> list[dict]:
    """为事件选项列表打分并返回新列表(原地追加 score 字段)."""

    event_prior = universe.event_prior[event_key]
    for choice in choices:
        choice["score"] = universe.event_score(choice["raw_text"], event_prior)
    return choices


def _sort_choices_by_score(choices: list[dict]) -> list[dict]:
    """按 score 倒序排序."""

    return sorted(choices, key=lambda x: x["score"], reverse=True)


def _log_scored_choices(choices: list[dict]) -> None:
    """打印打分结果(保持旧输出格式,不包含 box)."""

    print([{k: v for k, v in event.items() if k != "box"} for event in choices])


def _click_choice_until_confirm(universe, choices: list[dict]) -> bool:
    """依次尝试点击选项,直到出现确认按钮并点击确认."""

    for choice in choices:
        universe.click_box(choice["box"])
        time.sleep(0.4)
        universe.get_screen()
        if universe.check("confirm", 0.1828, 0.5000, mask="mask_event", threshold=0.965):
            universe.click((universe.tx, universe.ty))
            return True
    return False


def _choose_best_event_option(universe, event_key: str) -> bool:
    """在事件选择界面中按打分选择并点击确认."""

    choices = _parse_event_choices(universe)
    if not choices:
        return False

    _score_event_choices(universe, choices, event_key=event_key)
    choices = _sort_choices_by_score(choices)
    _log_scored_choices(choices)
    return _click_choice_until_confirm(universe, choices)


def _fallback_click_option(universe, tx: float, ty: float) -> None:
    """未能按规则点击到选项时的兜底逻辑."""

    universe.click((tx, ty))
    time.sleep(0.4)
    if universe.check("confirm", 0.1828, 0.5000, mask="mask_event", threshold=0.965):
        universe.click((universe.tx, universe.ty))
    else:
        universe.click((0.1167, ty - 0.4685 + 0.3546 + 0.02))


def _click_continue(universe, start: int) -> None:
    """事件对话/文本界面:点击右下角继续."""

    universe.click((0.9479, 0.9565))
    universe.click((0.9479, 0.9565))
    if start:
        universe.click((0.9479, 0.9565))
        universe.click((0.9479, 0.9565))
    universe.ts.forward(universe.get_screen())


def _try_click_exit(universe) -> bool:
    """事件界面:如出现返回/退出按钮则点击.

    Returns:
        True:已点击退出按钮
        False:未检测到退出按钮
    """

    if universe.check("arrow", 0.1828, 0.5000, mask="mask_event"):
        universe.click((universe.tx, universe.ty))
        return True
    if universe.check("arrow_1", 0.1828, 0.5000, mask="mask_event"):
        universe.click((universe.tx, universe.ty))
        return True
    return False


def _handle_star_choice_page(universe, event_key: Optional[str]) -> None:
    """事件选择界面:根据打分选择选项并确认."""

    tx, ty = universe.tx, universe.ty
    universe.ts.forward(universe.screen)

    # 旧版这里会在 debug 且无法解析事件时落盘 OCR 结果(test.txt),现已移除.

    clicked = False
    if event_key is not None:
        clicked = _choose_best_event_option(universe, event_key=event_key)

    if not clicked:
        _fallback_click_option(universe, tx, ty)

    time.sleep(0.8)


def _handle_default_event_flow(universe, start: int) -> bool:
    """其它情况:尝试点继续/刷新 OCR,必要时提前退出.

    Returns:
        True:已离开事件界面,应结束 handle_event
        False:仍在事件界面
    """

    if not start:
        time.sleep(0.6)
        universe.ts.forward(universe.get_screen())
        if not _is_in_event_page(universe):
            return True

    _click_continue(universe, start)
    return False


def handle_event(universe) -> None:
    """处理一次事件界面.

    Args:
        universe: DivergentUniverse 实例(为避免循环导入,这里不做显式类型标注).
    """

    event_key: Optional[str] = None
    universe.event_solved = 1

    start = 0
    tm = time.time()
    while time.time() - tm < 20:
        title_text = universe.clean_text(
            universe.ts.ocr_one_row(universe.screen, [185, 820, 945, 1005]), char=0
        )
        print(title_text)

        event_key, start = _resolve_event_key(universe, title_text, event_key)

        if not _is_in_event_page(universe):
            return

        universe.get_screen()

        if _try_click_exit(universe):
            continue

        if universe.check("star", 0.1828, 0.5000, mask="mask_event", threshold=0.965):
            _handle_star_choice_page(universe, event_key=event_key)
            start = 0
            continue

        if _handle_default_event_flow(universe, start=start):
            return


def find_event_text(universe) -> int:
    """定位事件交互点的大致水平位置.

    Returns:
        - 0:未找到
        - >0:x 坐标(返回 get_text_position 的最大项)
    """

    universe.get_screen()
    res = universe.get_text_position(clean=1)
    res = sorted(res, key=lambda x: x[0])
    if res:
        return res[-1][0]
    return 0


def _maybe_press_f_for_event_interaction(universe) -> bool:
    """若当前已出现交互提示则按下 F."""

    universe.get_screen()
    if universe.check_f(is_in=["事件", "奖励", "遭遇", "交易"]):
        universe.press("f")
        return True
    return False


def _maybe_find_event_text_first_pass(
    universe,
    key: str,
    deep: int,
    current_event_text: Optional[int],
) -> tuple[Optional[int], bool]:
    """第一次尝试定位事件文本位置,并返回 (event_text, found)."""

    found = False
    if deep == 0 and key == "d" and (current_event_text is None or current_event_text != 950):
        current_event_text = find_event_text(universe)
        if not current_event_text:
            universe.press("s", 1)
        else:
            found = True
    return current_event_text, found


def _ensure_event_text(universe, current_event_text: Optional[int], found: bool) -> int:
    """确保 event_text 有可用默认值(保持旧逻辑默认 950)."""

    if not found and not current_event_text:
        current_event_text = find_event_text(universe)
    return current_event_text or 950


def _normalize_align_key(current_key: str, current_event_text: int) -> str:
    """根据 event_text 修正对齐方向键."""

    if current_event_text < 910 and current_key == "d":
        return "a"
    return current_key


def _compute_align_steps(universe, current_event_text: int, current_key: str) -> int:
    """计算左右微调步数(保持旧经验参数与计算方式)."""

    if abs(950 - current_event_text) < 50:
        return 0

    event_text_after = find_event_text(universe)
    if event_text_after:
        delta = current_event_text - event_text_after
        if current_key == "a":
            delta = -delta
        print("sub:", delta)
        log.info(f"event_text_after: {event_text_after}, sub: {delta}")
    else:
        delta = 100000

    if delta < 60:
        delta = 100

    if delta < 400:
        steps = int((event_text_after - 950) / delta)
        return min(3, max(-3, int(steps)))
    return 2


def _apply_align_steps(universe, steps: int) -> None:
    """按计算步数执行左右移动."""

    for _ in range(steps):
        universe.press("d", 0.18)
        time.sleep(0.5)
    for _ in range(-steps):
        universe.press("a", 0.18)
        time.sleep(0.5)


def _maybe_click_and_close_pop(universe, click: int) -> None:
    """需要时点击并关闭可能弹窗."""

    if click:
        pyautogui.click()
        check_pop(universe)


def align_event(universe, key: str, deep: int = 0, event_text: Optional[int] = None, click: int = 0) -> None:
    """对齐事件交互点并靠近.

    该逻辑依赖大量“经验参数”,所以保持原流程,仅做模块迁移.
    """

    event_text, found = _maybe_find_event_text_first_pass(universe, key=key, deep=deep, current_event_text=event_text)
    event_text_value = _ensure_event_text(universe, event_text, found)
    key_normalized = _normalize_align_key(key, event_text_value)

    if _maybe_press_f_for_event_interaction(universe):
        return

    log.info(f"align_event: {event_text_value}, key: {key_normalized}")

    if abs(950 - event_text_value) >= 50:
        universe.press(key_normalized, 0.2)
        time.sleep(0.5)

    steps = _compute_align_steps(universe, event_text_value, key_normalized)
    _apply_align_steps(universe, steps)
    _maybe_click_and_close_pop(universe, click)
    universe.forward_until(["事件", "奖励", "遭遇", "交易"], timeout=2.5, moving=0, chaos=1)
