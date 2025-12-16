"""队伍成员识别与匹配工具.

该模块提供 diver/simul 可复用的“队伍成员名称匹配(子字符串兼容)”与
“队伍变化判断/远程站场位选择”等纯逻辑能力.

注意:
- 本模块不依赖具体 OCR 或 UI 行为;只处理结构化的 team_member 映射.
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence


def _name_matches(a: str, b: str) -> bool:
    """名称匹配:支持子字符串(兼容 OCR 缺字/别字的轻微偏差)."""

    if not a or not b:
        return False
    return a in b or b in a


def has_team_member(team_member: Mapping[str, int], char_name: str) -> bool:
    """检查队伍中是否包含指定角色(支持子字符串匹配)."""

    for member_name in team_member.keys():
        if _name_matches(char_name, member_name):
            return True
    return False


def get_team_member_position(
    team_member: Mapping[str, int], char_name: str
) -> Optional[int]:
    """获取队伍中指定角色的位置(支持子字符串匹配)."""

    for member_name, position in team_member.items():
        if _name_matches(char_name, member_name):
            return int(position)
    return None


def is_same_team(old_team: Mapping[str, int], new_team: Mapping[str, int]) -> bool:
    """判断两次识别到的队伍是否一致(角色名与位置都一致)."""

    if len(old_team) != len(new_team):
        return False

    for name, position in new_team.items():
        if name not in old_team or int(old_team[name]) != int(position):
            return False

    return True


def choose_long_range_slot(
    team_member: Mapping[str, int],
    long_range_list: Sequence[str],
) -> Optional[str]:
    """从队伍中选择一个“远程站场角色”的快捷键(1-4).

    返回:
    - None:队伍中没有匹配远程角色
    - str:对应角色所在位置 + 1(用于 universe.press)
    """

    for member_name, position in team_member.items():
        for long_range_name in long_range_list:
            if _name_matches(long_range_name, member_name):
                return str(int(position) + 1)

    return None
