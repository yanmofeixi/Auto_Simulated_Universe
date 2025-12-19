"""配置基类模块.

该模块提供配置类的公共基类,包括:
- 通用属性(multi, diffi)
- 配置文件读写的基础逻辑
- 按键映射处理
- JSON 数据文件加载
- 游戏窗口常量

供 simul 和 diver 的 Config 类继承复用.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Union

import yaml


# ===== 游戏窗口常量 =====
GAME_TITLE_PRIMARY = "崩坏：星穹铁道"
GAME_TITLE_SECONDARY = "云.星穹铁道"
GAME_WINDOW_CLASS = "UnityWndClass"
BASELINE_WIDTH = 1920
BASELINE_HEIGHT = 1080
FULLSCREEN_OFFSET_PX = 9


def is_game_window(title: str) -> bool:
    """判断窗口标题是否属于游戏窗口.

    Args:
        title: 窗口标题字符串

    Returns:
        如果是游戏窗口返回 True，否则返回 False
    """
    return title == GAME_TITLE_PRIMARY or title == GAME_TITLE_SECONDARY


class ConfigBase:
    """配置基类.

    提供 simul 和 diver 共享的配置功能.
    所有默认值都从 data/defaults.json 读取.

    Attributes:
        abspath (str): 项目根目录路径
        text (str): 配置文件名
        angle (str): 鼠标灵敏度设置
        difficult (str): 难度设置
        allow_difficult (list): 允许的难度值列表
        timezones (list): 支持的时区列表
        timezone (str): 当前时区
    """

    # ===== 类常量 =====
    DATA_DIR = "data"

    # 数据文件缓存 (类级别)
    _data_cache: Dict[str, Any] = {}
    _defaults_loaded: bool = False
    _defaults: Dict[str, Any] = {}

    def __init__(self):
        """初始化配置基类.

        所有默认值从 data/defaults.json 读取.
        """
        # 项目根目录
        self.abspath = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if getattr(sys, "frozen", False):
            self.abspath = "."

        # 配置文件
        self.text = "info.yml"

        # 加载默认值
        defaults = self._load_defaults()

        # 鼠标灵敏度和难度 (从 defaults.json 读取)
        self.angle = str(defaults.get("default_angle", 1.0))
        self.difficult = str(defaults.get("default_difficulty", 5))
        self.allow_difficult = [1, 2, 3, 4, 5]

        # 时区设置 (从 defaults.json 读取)
        timezones_data = defaults.get("timezones", [])
        self.timezones = [tz.get("value", "Default") for tz in timezones_data] if timezones_data else ["Default"]
        self.timezone = str(defaults.get("default_timezone", "Default"))

    @classmethod
    def _load_defaults(cls) -> Dict[str, Any]:
        """加载默认配置.

        使用类级别缓存避免重复加载.

        Returns:
            defaults.json 中的配置数据
        """
        if not cls._defaults_loaded:
            try:
                cls._defaults = cls.load_data_file("defaults.json")
                cls._defaults_loaded = True
            except (FileNotFoundError, json.JSONDecodeError):
                cls._defaults = {}
                cls._defaults_loaded = True
        return cls._defaults

    @property
    def multi(self) -> float:
        """获取鼠标灵敏度倍率.

        将 angle 字符串转换为实际的灵敏度倍率.

        逻辑:
        - x > 5: 无效值,重置为 1.0
        - x > 2: 返回 x - 2(用于表示 0-3 的范围)
        - x <= 2: 直接返回 x

        Returns:
            灵敏度倍率
        """
        x = float(self.angle)
        if x > 5:
            self.angle = "1.0"
            return 1.0
        elif x > 2:
            return x - 2
        else:
            return x

    @property
    def diffi(self) -> int:
        """获取难度等级.

        Returns:
            有效的难度等级,无效值返回默认值
        """
        diff = int(self.difficult)
        if diff in self.allow_difficult:
            return diff
        return self.allow_difficult[-1] if self.allow_difficult else 1

    def get_config_path(self) -> str:
        """获取配置文件完整路径.

        Returns:
            配置文件路径
        """
        return os.path.join(self.abspath, self.text)

    def load_yaml(self) -> Dict[str, Any]:
        """加载 YAML 配置文件.

        Returns:
            配置字典,文件不存在则返回空字典
        """
        config_path = self.get_config_path()
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                return yaml.safe_load(f) or {}
        return {}

    def save_yaml(self, data: Dict[str, Any]) -> None:
        """保存配置到 YAML 文件.

        Args:
            data: 要保存的配置字典
        """
        config_path = self.get_config_path()
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def read_common_config(self, config_data: Dict[str, Any]) -> None:
        """读取通用配置项.

        Args:
            config_data: 配置字典中的 'config' 部分
        """
        if not config_data:
            return

        self.angle = str(config_data.get("angle", self.angle))
        self.difficult = str(config_data.get("difficulty", self.difficult))
        self.timezone = str(config_data.get("timezone", self.timezone))

    def read(self) -> None:
        """读取配置文件.

        子类应重写此方法以添加特定配置项的读取.
        """
        data = self.load_yaml()
        if data:
            config_data = data.get("config", {})
            self.read_common_config(config_data)
        else:
            self.save()

    def save(self) -> None:
        """保存配置文件.

        子类应重写此方法以添加特定配置项的保存.
        """
        raise NotImplementedError("子类必须实现 save 方法")

    # ===== JSON 数据文件加载 =====

    @classmethod
    def _get_project_root(cls) -> str:
        """获取项目根目录.

        Returns:
            项目根目录路径
        """
        if getattr(sys, "frozen", False):
            return "."
        return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    @classmethod
    def load_data_file(cls, filename: str) -> Dict[str, Any]:
        """加载 JSON 数据文件.

        支持缓存,避免重复读取.

        Args:
            filename: 数据文件名(相对于 data 目录)

        Returns:
            解析后的 JSON 数据

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 解析失败
        """
        if filename in cls._data_cache:
            return cls._data_cache[filename]

        path = os.path.join(cls._get_project_root(), cls.DATA_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cls._data_cache[filename] = data
            return data

    @classmethod
    def clear_data_cache(cls) -> None:
        """清除数据文件缓存.

        用于测试或需要强制重新加载数据时.
        """
        cls._data_cache.clear()
        cls._defaults_loaded = False
        cls._defaults = {}

    @classmethod
    def get_default_threshold(cls) -> float:
        """获取默认阈值.

        Returns:
            默认阈值

        Raises:
            KeyError: 如果 defaults.json 中缺少 threshold 字段
        """
        defaults = cls.load_data_file("defaults.json")
        return float(defaults["threshold"])

    @classmethod
    def get_default_accuracy(cls) -> int:
        """获取默认精确度.

        Returns:
            默认精确度

        Raises:
            KeyError: 如果 defaults.json 中缺少 accuracy 字段
        """
        defaults = cls.load_data_file("defaults.json")
        return int(defaults["accuracy"])

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置.

        Returns:
            defaults.json 中的配置数据

        Raises:
            FileNotFoundError: 如果 defaults.json 不存在
            json.JSONDecodeError: 如果 JSON 解析失败
        """
        return cls.load_data_file("defaults.json")

    # ===== OCR 默认词表 =====

    @classmethod
    def get_ocr_defaults(cls) -> Dict[str, Any]:
        """获取 OCR 默认词表.

        Returns:
            ocr_defaults.json 中的数据

        Raises:
            FileNotFoundError: 如果 ocr_defaults.json 不存在
            json.JSONDecodeError: 如果 JSON 解析失败
        """
        return cls.load_data_file("ocr_defaults.json")

    @classmethod
    def get_fates(cls) -> List[str]:
        """获取命途列表.

        Returns:
            命途名称列表
        """
        defaults = cls.get_ocr_defaults()
        return list(defaults["fates"])

    @classmethod
    def get_prior_blessing(cls) -> List[str]:
        """获取优先祝福列表.

        Returns:
            优先祝福名称列表
        """
        defaults = cls.get_ocr_defaults()
        return list(defaults["prior_blessing"])

    @classmethod
    def get_secondary_fates(cls) -> List[str]:
        """获取次要命途列表.

        Returns:
            次要命途名称列表
        """
        defaults = cls.get_ocr_defaults()
        return list(defaults["secondary_fates"])

    @classmethod
    def get_curio(cls) -> List[str]:
        """获取奇物列表.

        Returns:
            奇物名称列表
        """
        defaults = cls.get_ocr_defaults()
        return list(defaults["curio"])

    @classmethod
    def get_blessings_by_fate(cls) -> List[List[str]]:
        """获取按命途分类的祝福列表.

        Returns:
            各命途的祝福列表
        """
        defaults = cls.get_ocr_defaults()
        return [list(items) for items in defaults["blessings_by_fate"]]

    @classmethod
    def get_interacts(cls, mode: str = "simul") -> List[str]:
        """获取交互关键词列表.

        Args:
            mode: 模式 ("simul" 或 "diver")

        Returns:
            交互关键词列表
        """
        defaults = cls.get_ocr_defaults()
        key = f"interacts_{mode}"
        return list(defaults[key])

    @classmethod
    def get_blessing_blacklist(cls) -> List[str]:
        """获取祝福黑名单.

        Returns:
            应跳过的祝福名称列表
        """
        defaults = cls.get_ocr_defaults()
        return list(defaults["blessing_blacklist"])
