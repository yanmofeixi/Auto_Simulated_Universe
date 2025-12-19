"""JSON 数据加载工具.

该模块提供读取 actions/*.json 并转换为内存结构的工具函数.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Dict, List, Union


JsonData = Union[Dict[str, List[str]], defaultdict]


def read_global_prior(file_path: str) -> Dict[str, Dict[str, int]]:
    """读取全局优先级配置文件 (global_prior.json).

        全局优先级具有最高权重,会在最后应用以覆盖其他配置.

        Args:
            file_path: JSON 文件路径.

        Returns:
            包含六个类别的优先级表:
            - 'blessing': 普通祝福优先级
            - 'equation': 方程选择优先级
            - 'boon': 金血祝福优先级
            - 'curio': 奇物优先级
            - 'weighted_curio': 加权奇物优先级
            - 'other': 其他 (fallback) 优先级
    i
            每个类别包含 {token: weight} 的字典,正数为白名单,负数为黑名单.
    """
    result: Dict[str, Dict[str, int]] = {
        "blessing": {},
        "equation": {},
        "boon": {},
        "curio": {},
        "weighted_curio": {},
        "other": {},
    }

    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 文件不存在或格式错误时返回空配置
        return result

    for category in [
        "blessing",
        "equation",
        "boon",
        "curio",
        "weighted_curio",
        "other",
    ]:
        if category in data:
            category_data = data[category]
            whitelist = category_data.get("whitelist", {})
            blacklist = category_data.get("blacklist", {})

            for token, weight in whitelist.items():
                result[category][token] = weight
            for token, weight in blacklist.items():
                result[category][token] = -weight

    return result


def read_team_prior(file_path: str) -> Dict[str, Dict[str, Dict[str, int]]]:
    """读取队伍类型优先级配置文件 (team_prior.json).

    队伍类型优先级具有中等权重,高于角色配置,低于全局配置.

    Args:
        file_path: JSON 文件路径.

    Returns:
        {队伍类型名称: {类别: {token: weight}}} 的嵌套字典.
        类别包含: blessing, equation, boon, curio, weighted_curio, other.
    """
    result: Dict[str, Dict[str, Dict[str, int]]] = {}

    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 文件不存在或格式错误时返回空配置
        return result

    for team_type, team_data in data.items():
        # 跳过 description 等非队伍类型字段
        if not isinstance(team_data, dict) or team_type == "description":
            continue

        result[team_type] = {
            "blessing": {},
            "equation": {},
            "boon": {},
            "curio": {},
            "weighted_curio": {},
            "other": {},
        }

        for category in [
            "blessing",
            "equation",
            "boon",
            "curio",
            "weighted_curio",
            "other",
        ]:
            if category in team_data:
                category_data = team_data[category]
                whitelist = category_data.get("whitelist", {})
                blacklist = category_data.get("blacklist", {})

                for token, weight in whitelist.items():
                    result[team_type][category][token] = weight
                for token, weight in blacklist.items():
                    result[team_type][category][token] = -weight

    return result


def read_actions_json(file_path: str, name: str) -> JsonData:
    """读取 actions/*.json 并返回结构化数据.

    Args:
        file_path: JSON 文件路径.
        name: 数据类型标识(例如:'char','blessing','event').
            'char' 返回四个类别的优先级表
            'blessing' 读取祝福信息 (blessing.json)
            'event' 读取事件配置

    Returns:
        - name == 'char': 包含六个 defaultdict 的字典:
            - 'blessing': 普通祝福优先级
            - 'equation': 方程选择优先级
            - 'boon': 金血祝福优先级
            - 'curio': 奇物优先级
            - 'weighted_curio': 加权奇物优先级
            - 'other': 其他 (fallback) 优先级
        - 其他: dict[str, list[str]], key 为名称.
    """

    with open(file_path, mode="r", encoding="utf-8") as f:
        data_list = json.load(f)

    if name == "char":
        # 返回六个独立的优先级表
        result = {
            "blessing": defaultdict(dict),  # 普通祝福
            "equation": defaultdict(dict),  # 方程选择
            "boon": defaultdict(dict),  # 金血祝福
            "curio": defaultdict(dict),  # 奇物
            "weighted_curio": defaultdict(dict),  # 加权奇物
            "other": defaultdict(dict),  # 其他 (fallback)
        }

        for item in data_list:
            char_name = item["name"]
            weight = item["weight"]

            # 解析普通祝福白名单和黑名单
            blessing_whitelist = item.get("blessing_whitelist", "")
            for token in blessing_whitelist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["blessing"][char_name][token] = weight
            blessing_blacklist = item.get("blessing_blacklist", "")
            for token in blessing_blacklist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["blessing"][char_name][token] = -weight

            # 解析方程选择白名单和黑名单
            equation_whitelist = item.get("equation_whitelist", "")
            for token in equation_whitelist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["equation"][char_name][token] = weight
            equation_blacklist = item.get("equation_blacklist", "")
            for token in equation_blacklist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["equation"][char_name][token] = -weight

            # 解析金血祝福白名单和黑名单
            boon_whitelist = item.get("boon_whitelist", "")
            for token in boon_whitelist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["boon"][char_name][token] = weight
            boon_blacklist = item.get("boon_blacklist", "")
            for token in boon_blacklist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["boon"][char_name][token] = -weight

            # 解析奇物白名单和黑名单
            curio_whitelist = item.get("curio_whitelist", "")
            for token in curio_whitelist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["curio"][char_name][token] = weight
            curio_blacklist = item.get("curio_blacklist", "")
            for token in curio_blacklist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["curio"][char_name][token] = -weight

            # 解析加权奇物白名单和黑名单
            weighted_curio_whitelist = item.get("weighted_curio_whitelist", "")
            for token in weighted_curio_whitelist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["weighted_curio"][char_name][token] = weight
            weighted_curio_blacklist = item.get("weighted_curio_blacklist", "")
            for token in weighted_curio_blacklist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["weighted_curio"][char_name][token] = -weight

            # 解析其他 (fallback) 白名单和黑名单
            other_whitelist = item.get("other_whitelist", "")
            for token in other_whitelist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["other"][char_name][token] = weight
            other_blacklist = item.get("other_blacklist", "")
            for token in other_blacklist.replace(",", ",").split(","):
                token = token.strip()
                if token:
                    result["other"][char_name][token] = -weight

        return result

    # 对于 blessing 和 event,返回 {name: [其他字段...]} 格式
    result_dict: Dict[str, List[str]] = {}
    for item in data_list:
        item_name = item["name"]
        if name == "blessing":
            # blessing: {name: [star, path]}
            result_dict[item_name] = [str(item.get("star", 0)), item.get("path", "")]
        elif name == "event":
            # event: {name: [priority, secondary, avoid]}
            result_dict[item_name] = [
                item.get("priority", "").replace(",", ","),
                item.get("secondary", "").replace(",", ","),
                item.get("avoid", "").replace(",", ","),
            ]
        else:
            # 通用格式
            values = [str(v).replace(",", ",") for k, v in item.items() if k != "name"]
            result_dict[item_name] = values

    return result_dict
