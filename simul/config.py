"""模拟宇宙配置模块."""

from __future__ import annotations

from typing import List

from utils.common.config_base import ConfigBase


class Config(ConfigBase):
    """模拟宇宙配置类.

    继承自 ConfigBase,添加模拟宇宙特有的配置项.
    从 data/ 目录加载静态数据 (命途列表、默认 prior 等).

    Attributes:
        order_text (str): 命途优先级顺序
        fate (str): 当前命途
        fates (list): 所有命途列表
        map_sha (str): 地图哈希值
        use_consumable (int): 是否使用消耗品
        unlock (int): 解锁状态
    """

    def __init__(self):
        """初始化模拟宇宙配置."""
        super().__init__()

        # ===== 从 data/defaults.json 加载默认值 =====
        defaults = self.get_default_config()

        # ===== 模拟宇宙特有配置 =====
        self.order_text = "1 2 3 4"
        self.fate = "巡猎"
        self.fates = list(defaults["simul_fates"])
        self.map_sha = ""

        # 模式开关
        self.use_consumable = 0
        self.unlock = 0

        # 读取配置
        self.read()

    @property
    def order(self) -> List[int]:
        """获取命途优先级顺序列表.

        Returns:
            命途优先级顺序的整数列表
        """
        return [int(i) for i in self.order_text.strip(" ").split(" ")]

    def read(self):
        """读取配置文件."""
        data = self.load_yaml()
        if data:
            config_data = data.get('config') or {}

            # 读取基类通用配置
            self.read_common_config(config_data)

            # 读取模拟宇宙特有配置
            try:
                order_value = config_data.get('order_text')
                if isinstance(order_value, list):
                    self.order_text = " ".join(str(x) for x in order_value)

                self.fate = str(config_data.get('fate', self.fate))
                self.map_sha = str(config_data.get('map_sha', self.map_sha))
                self.use_consumable = int(config_data.get('use_consumable', self.use_consumable) or 0)
            except (KeyError, ValueError, TypeError):
                pass
        else:
            self.save()

    def save(self):
        """保存配置文件."""
        # 尝试保留已有的 secondary_fate 和 prior 配置
        existing_data = self.load_yaml()
        defaults = self.get_default_config()
        ocr_defaults = self.get_ocr_defaults()

        secondary_fate = list(ocr_defaults["secondary_fates"])
        prior = defaults["simul_prior"]

        if existing_data:
            try:
                existing_config = existing_data.get('config', {})
                if 'secondary_fate' in existing_config:
                    secondary_fate = existing_config['secondary_fate']
            except (KeyError, TypeError):
                pass

            try:
                if 'prior' in existing_data:
                    prior = existing_data['prior']
            except (KeyError, TypeError):
                pass

        self.save_yaml({
            "config": {
                "order_text": list(map(lambda x: int(x), self.order_text.split(' '))),
                "angle": float(self.angle),
                "difficulty": self.diffi,
                "fate": self.fate,
                "secondary_fate": secondary_fate,
                "map_sha": self.map_sha,
                "use_consumable": self.use_consumable,
                "timezone": self.timezone,
            },
            "prior": prior,
        })

    def _get_default_prior(self) -> dict:
        """获取默认的优先级配置.

        从 data/defaults.json 加载.

        Returns:
            默认优先级字典
        """
        defaults = self.load_data_file("defaults.json")
        return defaults["simul_prior"]

    @property
    def default_threshold(self) -> float:
        """默认匹配阈值."""
        return self.DEFAULT_THRESHOLD


config = Config()
