"""配置基类模块.

该模块提供配置类的公共基类,包括:
- 通用属性(multi, diffi)
- 配置文件读写的基础逻辑
- 按键映射处理

供 simul 和 diver 的 Config 类继承复用.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Union

import yaml


class ConfigBase:
    """配置基类.

    提供 simul 和 diver 共享的配置功能.

    Attributes:
        abspath (str): 项目根目录路径
        text (str): 配置文件名
        angle (str): 鼠标灵敏度设置
        difficult (str): 难度设置
        allow_difficult (list): 允许的难度值列表
        timezones (list): 支持的时区列表
        timezone (str): 当前时区
        origin_key (list): 原始按键映射
        mapping (list): 当前按键映射
    """

    def __init__(self):
        """初始化配置基类."""
        # 项目根目录
        self.abspath = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if getattr(sys, 'frozen', False):
            self.abspath = '.'

        # 配置文件
        self.text = "info.yml"

        # 鼠标灵敏度和难度
        self.angle = "1.0"
        self.difficult = "5"
        self.allow_difficult = [1, 2, 3, 4, 5]

        # 时区设置
        self.timezones = ['America', 'Asia', 'Europe', 'Default']
        self.timezone = 'Default'

        # 按键映射
        self.origin_key = ['f', 'm', 'shift', 'v', 'e', 'w', 'a', 's', 'd', '1', '2', '3', '4']
        self.mapping = self.origin_key.copy()

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
            self.angle = '1.0'
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
            with open(config_path, "r", encoding="utf-8", errors='ignore') as f:
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

        self.angle = str(config_data.get('angle', self.angle))
        self.difficult = str(config_data.get('difficulty', self.difficult))
        self.timezone = str(config_data.get('timezone', self.timezone))

    def read_key_mapping(self, data: Dict[str, Any]) -> None:
        """读取按键映射配置.

        Args:
            data: 完整配置字典
        """
        mapping_value = data.get('key_mapping')
        if isinstance(mapping_value, list) and mapping_value:
            self.mapping = [str(x) for x in mapping_value]

    def read(self) -> None:
        """读取配置文件.

        子类应重写此方法以添加特定配置项的读取.
        """
        data = self.load_yaml()
        if data:
            config_data = data.get('config', {})
            self.read_common_config(config_data)
            self.read_key_mapping(data)
        else:
            self.save()

    def save(self) -> None:
        """保存配置文件.

        子类应重写此方法以添加特定配置项的保存.
        """
        raise NotImplementedError("子类必须实现 save 方法")
