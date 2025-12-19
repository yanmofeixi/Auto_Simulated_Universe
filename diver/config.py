"""差分宇宙配置模块."""

from __future__ import annotations

from typing import Any, List

from utils.common.config_base import ConfigBase


class Config(ConfigBase):
    """差分宇宙配置类.

    继承自 ConfigBase,添加差分宇宙特有的配置项.
    从 data/ 目录加载静态数据 (角色列表,视角角度表等).

    Attributes:
        skill_char (list): 秘技角色列表
        accuracy (int): 精确度
        enable_portal_prior (int): 是否启用传送门优先级
        portal_prior (dict): 传送门优先级配置
        team (str): 队伍类型
    """

    # 缓存属性
    _all_list: List[str] = None
    _long_range_list: List[str] = None
    _angles: List[int] = None

    def __init__(self):
        """初始化差分宇宙配置."""
        super().__init__()

        # ===== 从 data/defaults.json 加载默认值 =====
        defaults = self.get_default_config()

        # ===== 差分宇宙特有配置 =====
        # 从 data/characters.json 加载默认秘技角色
        char_data = self.load_data_file("characters.json")
        self.skill_char = list(char_data.get("skill_characters", []))

        # 精确度
        self.accuracy = defaults["accuracy"]

        # 传送门优先级
        self.enable_portal_prior = 0
        self.portal_prior = dict(defaults["diver_portal_prior"])

        # 队伍类型
        self.team = defaults["default_team"]

        # OCR 是否使用 GPU 加速(小模型场景下 CPU 反而更快)
        self.ocr_use_gpu = False

        # 读取配置
        self.read()

    # ===== 延迟加载属性 =====

    @property
    def all_list(self) -> List[str]:
        """所有角色列表 (从 data/characters.json 延迟加载)."""
        if Config._all_list is None:
            data = self.load_data_file("characters.json")
            Config._all_list = data.get("all_characters", [])
        return Config._all_list

    @property
    def long_range_list(self) -> List[str]:
        """远程角色列表 (从 data/characters.json 延迟加载)."""
        if Config._long_range_list is None:
            data = self.load_data_file("characters.json")
            Config._long_range_list = data.get("long_range_characters", [])
        return Config._long_range_list

    @property
    def angles(self) -> List[int]:
        """视角角度映射表 (从 data/angles.json 延迟加载,已反转)."""
        if Config._angles is None:
            data = self.load_data_file("angles.json")
            Config._angles = data.get("portal_angles", [])[::-1]
        return Config._angles

    @property
    def default_threshold(self) -> float:
        """默认匹配阈值 (从 defaults.json 读取)."""
        return self.get_default_threshold()

    @property
    def default_long_range_slot(self) -> str:
        """默认远程角色槽位."""
        defaults = self.get_default_config()
        return defaults["default_long_range_slot"]

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
                    "ocr_use_gpu": self.ocr_use_gpu,
                },
            }
        )


config = Config()
