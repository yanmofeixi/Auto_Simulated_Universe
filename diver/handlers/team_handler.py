"""差分宇宙队伍与站场角色选择处理器."""

from __future__ import annotations

import time
from typing import Dict

from diver.config import config
from utils.common import team_utils
from utils.log import log


def _match_character(name: str, char_names: list) -> str | None:
    """尝试匹配角色名称."""
    if name in char_names:
        return name
    for char_name in char_names:
        if char_name in name or name in char_name:
            return char_name
    return None


def detect_team_members(universe) -> Dict[str, int]:
    """识别队伍成员并返回 {角色名: 位置}.

    每个 area 识别一次:
    - 如果已经识别出 4 个队员,直接返回缓存结果,不再重新识别
    - 否则重新识别,如果识别出更多角色就保留更多的结果
    """

    # 如果已经识别出 4 个队员,不再重新识别
    if len(universe.team_member) >= 4:
        return universe.team_member

    boxes = [
        [1620, 1790, 289, 335],
        [1620, 1790, 384, 427],
        [1620, 1790, 478, 521],
        [1620, 1790, 570, 618],
    ]
    char_names = config.all_list

    tm_start = time.time()
    new_team_member: Dict[str, int] = {}

    log.info(f"开始识别队伍成员 (当前已识别: {len(universe.team_member)} 人)...")
    for index, box in enumerate(boxes):
        name = universe.clean_text(universe.ts.ocr_one_row(universe.get_screen(), box))
        found_char = _match_character(name, char_names)

        if found_char is not None and found_char not in new_team_member:
            new_team_member[found_char] = index
            log.info(f"区域 {index}: 识别到 {found_char}")
        else:
            log.info(f"区域 {index}: 未识别到角色 (OCR: {name})")

    # 如果新识别出更多角色,保留更多的结果
    if len(new_team_member) > len(universe.team_member):
        log.info(
            f"识别到更多队员: {len(universe.team_member)} -> {len(new_team_member)}, 更新队伍信息"
        )
        result = new_team_member
    else:
        log.info(f"未识别到更多队员,保留原有结果")
        result = universe.team_member if universe.team_member else new_team_member

    log.info(
        f"队伍成员识别完成: {result}, 总耗时: {int((time.time()-tm_start)*1000)}ms"
    )
    return result


def sync_team_state_and_long_range(universe, team_member: Dict[str, int]) -> bool:
    """同步队伍状态,并在变化时更新远程站场角色.

    Returns:
        True:队伍有更新
        False:队伍未变化(跳过更新)
    """

    # 如果新识别的队伍成员数量不超过现有的,跳过更新
    if len(team_member) <= len(universe.team_member):
        return False

    # 更新队伍信息
    universe.team_member = team_member
    log.info(f"队伍状态已同步: {team_member}")

    # 从当前队伍中,选取处于内置远程角色列表中的第一个远程角色
    long_range_slot = team_utils.choose_long_range_slot(
        universe.team_member,
        config.long_range_list,
    )
    if long_range_slot is not None:
        universe.long_range = long_range_slot

    return True


def prepare_active_character(universe, area_now: str) -> None:
    """根据队伍成员与秘技配置,决定站场角色并切换.

    该逻辑会更新:
    - `universe.da_hei_ta` / `universe.bai_e` / `universe.quan`
    """

    # 判断队伍成员状态(使用子字符串匹配)
    da_hei_ta_in_team = universe.has_team_member("大黑塔")
    bai_e_in_team = universe.has_team_member("白厄")
    huang_quan_in_team = universe.has_team_member("黄泉")

    # 判断秘技状态
    da_hei_ta_has_skill = "大黑塔" in config.skill_char
    bai_e_has_skill = "白厄" in config.skill_char
    huang_quan_has_skill = "黄泉" in config.skill_char

    # 优先级: 白厄 -> 大黑塔 -> 黄泉 -> 远程角色
    if bai_e_in_team and bai_e_has_skill:
        universe.bai_e = 1

    elif da_hei_ta_in_team and da_hei_ta_has_skill:
        universe.da_hei_ta = True

    elif huang_quan_in_team and huang_quan_has_skill:
        universe.quan = 1

    else:
        universe.da_hei_ta = False
        universe.bai_e = 0
        universe.quan = 0

    # 决策站场角色:大黑塔通用;白厄/黄泉倾向战斗
    if not universe.allow_e:
        universe.press(universe.long_range)
        return

    if universe.da_hei_ta:
        pos = universe.get_team_member_position("大黑塔")
        universe.press(str(pos + 1))
        return

    if universe.bai_e and area_now == "战斗":
        pos = universe.get_team_member_position("白厄")
        universe.press(str(pos + 1))
        return

    if universe.quan and area_now == "战斗":
        pos = universe.get_team_member_position("黄泉")
        universe.press(str(pos + 1))
        return

    universe.press(universe.long_range)
