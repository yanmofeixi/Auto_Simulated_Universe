"""差分宇宙配置模块."""

from __future__ import annotations

import os
from typing import Any, List

import yaml

from utils.common.config_base import ConfigBase


class Config(ConfigBase):
    """差分宇宙配置类.

    继承自 ConfigBase,添加差分宇宙特有的配置项.

    Attributes:
        skill_char (list): 秘技角色列表
        long_range_list (list): 远程角色列表
        all_list (list): 所有角色列表
        angles (list): 视角角度映射表
        accuracy (int): 精确度
        enable_portal_prior (int): 是否启用传送门优先级
        portal_prior (dict): 传送门优先级配置
        team (str): 队伍类型
    """

    def __init__(self):
        """初始化差分宇宙配置."""
        super().__init__()

        # ===== 差分宇宙特有配置 =====
        self.skill_char = ["符玄", "阮梅", "黄泉", "白厄"]

        # 远程角色列表
        self.long_range_list = ["阮梅", "灵砂", "缇宝", "刻律"]

        # 所有角色列表
        self.all_list = [
            "流萤",
            "黄泉",
            "波提欧",
            "真理医生",
            "饮月",
            "瓦尔特杨",
            "克拉拉",
            "银枝",
            "刃",
            "希儿",
            "景元",
            "镜流",
            "卡芙卡",
            "托帕账账",
            "黑天鹅",
            "翡翠",
            "云璃",
            "砂金",
            "椒丘",
            "彦卿",
            "姬子",
            "杰帕德",
            "藿藿",
            "白露",
            "阿兰",
            "素裳",
            "加拉赫",
            "知更鸟",
            "阮梅",
            "布洛妮娅",
            "花火",
            "符玄",
            "银狼",
            "罗刹",
            "寒鸦",
            "卢卡",
            "桂乃芬",
            "虎克",
            "艾丝妲",
            "米沙",
            "佩拉",
            "黑塔",
            "三月七",
            "停云",
            "桑博",
            "雪衣",
            "青雀",
            "玲可",
            "驭空",
            "娜塔莎",
            "希露瓦",
            "大黑塔",
            "忘归人",
            "星期日",
            "灵砂",
            "缇宝",
            "白厄",
            "刻律",
            "丹恒",
        ]

        # 视角角度映射表(用于传送门瞄准)
        self.angles = [
            912,
            891,
            870,
            848,
            828,
            805,
            784,
            765,
            745,
            724,
            704,
            685,
            667,
            648,
            629,
            612,
            594,
            574,
            557,
            538,
            523,
            505,
            489,
            472,
            456,
            438,
            422,
            408,
            391,
            374,
            358,
            342,
            327,
            313,
            297,
            280,
            265,
            251,
            235,
            222,
            205,
            192,
            160,
            146,
            134,
            118,
            101,
            87,
            73,
            59,
            44,
            28,
            12,
            0,
            -14,
            -31,
            -45,
            -56,
            -76,
            -89,
            -99,
            -117,
            -131,
            -145,
            -152,
            -173,
            -196,
            -206,
            -221,
            -235,
            -255,
            -268,
            -284,
            -297,
            -311,
            -329,
            -339,
            -354,
            -375,
            -391,
            -407,
            -422,
            -440,
            -457,
            -473,
            -486,
            -506,
            -523,
            -540,
            -555,
            -576,
            -592,
            -613,
            -630,
            -649,
            -668,
            -687,
            -707,
            -725,
            -744,
            -765,
            -786,
            -807,
            -827,
            -849,
            -872,
            -893,
            -907,
            -918,
        ][::-1]

        # 精确度
        self.accuracy = 1440

        # 传送门优先级
        self.enable_portal_prior = 0
        self.portal_prior = {
            "奖励": 3,
            "事件": 3,
            "战斗": 2,
            "遭遇": 2,
            "商店": 1,
            "财富": 1,
        }

        # 队伍类型
        self.team = "终结技"

        # OCR 是否使用 GPU 加速（小模型场景下 CPU 反而更快）
        self.ocr_use_gpu = False

        # 读取配置
        self.read()

    def clean_text(self, text, char=1):
        """复用共享实现:保持旧签名不变."""
        from utils.common.text_utils import clean_text as common_clean_text

        return common_clean_text(text, char=char)

    def update_skill(self, skill: List[str]):
        """更新秘技角色列表.

        Args:
            skill: 角色名称列表
        """
        self.skill_char = []
        for i in skill:
            i = self.clean_text(i, 0)
            # 匹配全部角色
            if i in self.all_list:
                self.skill_char.append(i)
            elif i in ["1", "2", "3", "4"]:
                self.skill_char.append(i)

    def read(self):
        """读取配置文件."""
        data = self.load_yaml()
        if data:
            config_data: Any = data.get("config") or {}

            # 读取基类通用配置
            self.read_common_config(config_data)
            self.read_key_mapping(data)

            # 读取差分宇宙特有配置
            self.team = str(config_data.get("team", self.team))
            self.accuracy = int(
                config_data.get("accuracy", self.accuracy) or self.accuracy
            )
            self.enable_portal_prior = int(
                config_data.get("enable_portal_prior", self.enable_portal_prior) or 0
            )

            skill_value = config_data.get("skill")
            if isinstance(skill_value, list):
                self.update_skill([str(x) for x in skill_value])

            portal_prior_value = config_data.get("portal_prior")
            if isinstance(portal_prior_value, dict):
                self.portal_prior = portal_prior_value

            # 读取 OCR GPU 配置
            self.ocr_use_gpu = bool(config_data.get("ocr_use_gpu", self.ocr_use_gpu))
        else:
            self.save()

    def save(self):
        """保存配置文件."""
        self.save_yaml(
            {
                "config": {
                    "angle": float(self.angle),
                    "difficulty": self.diffi,
                    "team": self.team,
                    "skill": self.skill_char,
                    "timezone": self.timezone,
                    "accuracy": self.accuracy,
                    "enable_portal_prior": self.enable_portal_prior,
                    "portal_prior": self.portal_prior,
                },
                "key_mapping": self.mapping,
            }
        )


config = Config()
