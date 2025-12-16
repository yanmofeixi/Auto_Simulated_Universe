"""差分宇宙:策略/打分相关的纯函数.

该模块提供事件选项与各类选择相关的打分/构建函数:
- 普通祝福 (blessing): 祝福选择时触发
- 方程选择 (equation): 方程选择时触发
- 金血祝福 (boon): 金血祝福选择时触发
- 奇物 (curio): 奇物选择时触发
- 加权奇物 (weighted_curio): 加权奇物选择时触发
- 其他 (other): 作为 fallback 使用

优先级顺序 (从低到高):
1. 角色配置 (character_prior.json) - 基础权重
2. 队伍类型配置 (team_prior.json) - 权重乘以 TEAM_PRIORITY_MULTIPLIER
3. 全局配置 (global_prior.json) - 权重乘以 GLOBAL_PRIORITY_MULTIPLIER (最高优先级)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Mapping, Optional

# 队伍类型配置的权重乘数
TEAM_PRIORITY_MULTIPLIER = 5

# 全局配置的权重乘数，确保全局配置具有最高优先级
GLOBAL_PRIORITY_MULTIPLIER = 10


def score_event_choice(text: str, event_rule: Iterable[str]) -> int:
    """事件选项打分.

    规则:
    - event_rule 长度为 3(偏好/普通/强烈不选),每项允许用 '-' 分隔多个关键词.
    - 固定权重:偏好/普通/强烈不选 -> 2/1/-10.
    """

    score = 0
    event_weight = [2, 1, -10]
    event_rule_list = list(event_rule)
    for index in range(3):
        for token in event_rule_list[index].split("-"):
            if token and token in text:
                score += event_weight[index]
    return score


def build_blessing_prior(
    team_member_names: Iterable[str],
    character_prior: Mapping[str, Mapping[str, Mapping[str, int]]],
    team_type: str,
    team_prior: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]] = None,
    global_prior: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> defaultdict:
    """根据角色配置 + 队伍类型配置 + 全局配置,构建普通祝福关键词优先级表.

    普通祝福 (blessing): 祝福选择时触发.

    优先级顺序 (从低到高):
    1. 角色配置 (基础权重)
    2. 队伍类型配置 (权重乘以 TEAM_PRIORITY_MULTIPLIER)
    3. 全局配置 (权重乘以 GLOBAL_PRIORITY_MULTIPLIER)

    Args:
        team_member_names: 队伍成员名称列表.
        character_prior: 角色优先级配置字典,包含 blessing/boon/curio/weighted_curio.
        team_type: 队伍类型.
        team_prior: 队伍类型优先级配置字典 (可选).
        global_prior: 全局优先级配置字典 (可选).

    Returns:
        祝福关键词优先级表 {关键词: 权重}.
    """
    blessing_prior: defaultdict = defaultdict(int)
    blessing_data = character_prior.get("blessing", {})

    # 1. 先处理角色配置 (最低优先级)
    for name in list(team_member_names):
        if name in blessing_data:
            prior = blessing_data[name]
            for token, weight in prior.items():
                blessing_prior[token] += weight

    # 2. 处理队伍类型配置 (中等优先级)
    if team_prior and team_type in team_prior:
        team_blessing = team_prior[team_type].get("blessing", {})
        for token, weight in team_blessing.items():
            blessing_prior[token] += weight * TEAM_PRIORITY_MULTIPLIER

    # 3. 最后处理全局配置 (最高优先级)
    if global_prior and "blessing" in global_prior:
        for token, weight in global_prior["blessing"].items():
            blessing_prior[token] += weight * GLOBAL_PRIORITY_MULTIPLIER

    return blessing_prior


def build_equation_prior(
    team_member_names: Iterable[str],
    character_prior: Mapping[str, Mapping[str, Mapping[str, int]]],
    team_type: str,
    team_prior: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]] = None,
    global_prior: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> defaultdict:
    """根据角色配置 + 队伍类型配置 + 全局配置,构建方程选择关键词优先级表.

    方程选择 (equation): 方程选择时触发.

    优先级顺序 (从低到高):
    1. 角色配置 (基础权重)
    2. 队伍类型配置 (权重乘以 TEAM_PRIORITY_MULTIPLIER)
    3. 全局配置 (权重乘以 GLOBAL_PRIORITY_MULTIPLIER)

    Args:
        team_member_names: 队伍成员名称列表.
        character_prior: 角色优先级配置字典.
        team_type: 队伍类型.
        team_prior: 队伍类型优先级配置字典 (可选).
        global_prior: 全局优先级配置字典 (可选).

    Returns:
        方程选择关键词优先级表 {关键词: 权重}.
    """
    equation_prior: defaultdict = defaultdict(int)
    equation_data = character_prior.get("equation", {})

    # 1. 先处理角色配置 (最低优先级)
    for name in list(team_member_names):
        if name in equation_data:
            prior = equation_data[name]
            for token, weight in prior.items():
                equation_prior[token] += weight

    # 2. 处理队伍类型配置 (中等优先级)
    if team_prior and team_type in team_prior:
        team_equation = team_prior[team_type].get("equation", {})
        for token, weight in team_equation.items():
            equation_prior[token] += weight * TEAM_PRIORITY_MULTIPLIER

    # 3. 最后处理全局配置 (最高优先级)
    if global_prior and "equation" in global_prior:
        for token, weight in global_prior["equation"].items():
            equation_prior[token] += weight * GLOBAL_PRIORITY_MULTIPLIER

    return equation_prior


def build_boon_prior(
    team_member_names: Iterable[str],
    character_prior: Mapping[str, Mapping[str, Mapping[str, int]]],
    team_type: str,
    team_prior: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]] = None,
    global_prior: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> defaultdict:
    """根据角色配置 + 队伍类型配置 + 全局配置,构建金血祝福关键词优先级表.

    金血祝福 (boon): 金血祝福选择时触发.

    优先级顺序 (从低到高):
    1. 角色配置 (基础权重)
    2. 队伍类型配置 (权重乘以 TEAM_PRIORITY_MULTIPLIER)
    3. 全局配置 (权重乘以 GLOBAL_PRIORITY_MULTIPLIER)

    Args:
        team_member_names: 队伍成员名称列表.
        character_prior: 角色优先级配置字典,包含 blessing/boon/curio/weighted_curio.
        team_type: 队伍类型.
        team_prior: 队伍类型优先级配置字典 (可选).
        global_prior: 全局优先级配置字典 (可选).

    Returns:
        金血祝福关键词优先级表 {关键词: 权重}.
    """
    boon_prior: defaultdict = defaultdict(int)
    boon_data = character_prior.get("boon", {})

    # 1. 先处理角色配置 (最低优先级)
    for name in list(team_member_names):
        if name in boon_data:
            prior = boon_data[name]
            for token, weight in prior.items():
                boon_prior[token] += weight

    # 2. 处理队伍类型配置 (中等优先级)
    if team_prior and team_type in team_prior:
        team_boon = team_prior[team_type].get("boon", {})
        for token, weight in team_boon.items():
            boon_prior[token] += weight * TEAM_PRIORITY_MULTIPLIER

    # 3. 最后处理全局配置 (最高优先级)
    if global_prior and "boon" in global_prior:
        for token, weight in global_prior["boon"].items():
            boon_prior[token] += weight * GLOBAL_PRIORITY_MULTIPLIER

    return boon_prior


def build_curio_prior(
    team_member_names: Iterable[str],
    character_prior: Mapping[str, Mapping[str, Mapping[str, int]]],
    team_type: str,
    team_prior: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]] = None,
    global_prior: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> defaultdict:
    """根据角色配置 + 队伍类型配置 + 全局配置,构建奇物关键词优先级表.

    奇物 (curio): 奇物选择时触发.

    优先级顺序 (从低到高):
    1. 角色配置 (基础权重)
    2. 队伍类型配置 (权重乘以 TEAM_PRIORITY_MULTIPLIER)
    3. 全局配置 (权重乘以 GLOBAL_PRIORITY_MULTIPLIER)

    Args:
        team_member_names: 队伍成员名称列表.
        character_prior: 角色优先级配置字典,包含 blessing/boon/curio/weighted_curio.
        team_type: 队伍类型.
        team_prior: 队伍类型优先级配置字典 (可选).
        global_prior: 全局优先级配置字典 (可选).

    Returns:
        奇物关键词优先级表 {关键词: 权重}.
    """
    curio_prior: defaultdict = defaultdict(int)
    curio_data = character_prior.get("curio", {})

    # 1. 先处理角色配置 (最低优先级)
    for name in list(team_member_names):
        if name in curio_data:
            prior = curio_data[name]
            for token, weight in prior.items():
                curio_prior[token] += weight

    # 2. 处理队伍类型配置 (中等优先级)
    if team_prior and team_type in team_prior:
        team_curio = team_prior[team_type].get("curio", {})
        for token, weight in team_curio.items():
            curio_prior[token] += weight * TEAM_PRIORITY_MULTIPLIER

    # 3. 最后处理全局配置 (最高优先级)
    if global_prior and "curio" in global_prior:
        for token, weight in global_prior["curio"].items():
            curio_prior[token] += weight * GLOBAL_PRIORITY_MULTIPLIER

    return curio_prior


def build_weighted_curio_prior(
    team_member_names: Iterable[str],
    character_prior: Mapping[str, Mapping[str, Mapping[str, int]]],
    team_type: str,
    team_prior: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]] = None,
    global_prior: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> defaultdict:
    """根据角色配置 + 队伍类型配置 + 全局配置,构建加权奇物关键词优先级表.

    加权奇物 (weighted_curio): 加权奇物选择时触发.

    优先级顺序 (从低到高):
    1. 角色配置 (基础权重)
    2. 队伍类型配置 (权重乘以 TEAM_PRIORITY_MULTIPLIER)
    3. 全局配置 (权重乘以 GLOBAL_PRIORITY_MULTIPLIER)

    Args:
        team_member_names: 队伍成员名称列表.
        character_prior: 角色优先级配置字典,包含 blessing/boon/curio/weighted_curio.
        team_type: 队伍类型.
        team_prior: 队伍类型优先级配置字典 (可选).
        global_prior: 全局优先级配置字典 (可选).

    Returns:
        加权奇物关键词优先级表 {关键词: 权重}.
    """
    weighted_curio_prior: defaultdict = defaultdict(int)
    weighted_curio_data = character_prior.get("weighted_curio", {})

    # 1. 先处理角色配置 (最低优先级)
    for name in list(team_member_names):
        if name in weighted_curio_data:
            prior = weighted_curio_data[name]
            for token, weight in prior.items():
                weighted_curio_prior[token] += weight

    # 2. 处理队伍类型配置 (中等优先级)
    if team_prior and team_type in team_prior:
        team_weighted_curio = team_prior[team_type].get("weighted_curio", {})
        for token, weight in team_weighted_curio.items():
            weighted_curio_prior[token] += weight * TEAM_PRIORITY_MULTIPLIER

    # 3. 最后处理全局配置 (最高优先级)
    if global_prior and "weighted_curio" in global_prior:
        for token, weight in global_prior["weighted_curio"].items():
            weighted_curio_prior[token] += weight * GLOBAL_PRIORITY_MULTIPLIER

    return weighted_curio_prior


def score_blessing(
    text: str, blessing_prior: Mapping[str, int], all_blessing: Mapping[str, list]
) -> int:
    """普通祝福打分 (祝福选择时使用).

    Args:
        text: 祝福文本.
        blessing_prior: 祝福关键词优先级表.
        all_blessing: 所有祝福信息.

    Returns:
        祝福得分.
    """
    score = 0
    for token, weight in blessing_prior.items():
        if token in text:
            score += weight

    for key, values in all_blessing.items():
        # 用 key 的后 4 个字符匹配祝福名称
        if key[-4:] in text:
            score += int(values[0]) - 1

    return score


def score_equation(
    text: str,
    equation_prior: Mapping[str, int],
) -> int:
    """方程选择打分.

    Args:
        text: 方程选择文本.
        equation_prior: 方程选择关键词优先级表.

    Returns:
        方程选择得分.
    """
    score = 0
    for token, weight in equation_prior.items():
        if token in text:
            score += weight
    return score


def score_boon(
    text: str,
    boon_prior: Mapping[str, int],
) -> int:
    """金血祝福打分.

    Args:
        text: 金血祝福文本.
        boon_prior: 金血祝福关键词优先级表.

    Returns:
        金血祝福得分.
    """
    score = 0
    for token, weight in boon_prior.items():
        if token in text:
            score += weight
    return score


def score_curio(
    text: str,
    curio_prior: Mapping[str, int],
) -> int:
    """奇物打分.

    Args:
        text: 奇物文本.
        curio_prior: 奇物关键词优先级表.

    Returns:
        奇物得分.
    """
    score = 0
    for token, weight in curio_prior.items():
        if token in text:
            score += weight
    return score


def score_weighted_curio(
    text: str,
    weighted_curio_prior: Mapping[str, int],
) -> int:
    """加权奇物打分.

    Args:
        text: 加权奇物文本.
        weighted_curio_prior: 加权奇物关键词优先级表.

    Returns:
        加权奇物得分.
    """
    score = 0
    for token, weight in weighted_curio_prior.items():
        if token in text:
            score += weight
    return score


def build_other_prior(
    team_member_names: Iterable[str],
    character_prior: Mapping[str, Mapping[str, Mapping[str, int]]],
    team_type: str,
    team_prior: Optional[Mapping[str, Mapping[str, Mapping[str, int]]]] = None,
    global_prior: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> defaultdict:
    """根据角色配置 + 队伍类型配置 + 全局配置,构建其他 (fallback) 关键词优先级表.

    其他 (other): 作为 fallback 使用,当主要类别得分为 0 时使用.

    优先级顺序 (从低到高):
    1. 角色配置 (基础权重)
    2. 队伍类型配置 (权重乘以 TEAM_PRIORITY_MULTIPLIER)
    3. 全局配置 (权重乘以 GLOBAL_PRIORITY_MULTIPLIER)

    Args:
        team_member_names: 队伍成员名称列表.
        character_prior: 角色优先级配置字典.
        team_type: 队伍类型.
        team_prior: 队伍类型优先级配置字典 (可选).
        global_prior: 全局优先级配置字典 (可选).

    Returns:
        其他关键词优先级表 {关键词: 权重}.
    """
    other_prior: defaultdict = defaultdict(int)
    other_data = character_prior.get("b", {})

    # 1. 先处理角色配置 (最低优先级)
    for name in list(team_member_names):
        if name in other_data:
            prior = other_data[name]
            for token, weight in prior.items():
                other_prior[token] += weight

    # 2. 处理队伍类型配置 (中等优先级)
    if team_prior and team_type in team_prior:
        team_other = team_prior[team_type].get("other", {})
        for token, weight in team_other.items():
            other_prior[token] += weight * TEAM_PRIORITY_MULTIPLIER

    # 3. 最后处理全局配置 (最高优先级)
    if global_prior and "other" in global_prior:
        for token, weight in global_prior["other"].items():
            other_prior[token] += weight * GLOBAL_PRIORITY_MULTIPLIER

    return other_prior


def score_other(
    text: str,
    other_prior: Mapping[str, int],
) -> int:
    """其他 (fallback) 打分.

    Args:
        text: 待打分文本.
        other_prior: 其他关键词优先级表.

    Returns:
        得分.
    """
    score = 0
    for token, weight in other_prior.items():
        if token in text:
            score += weight
    return score
