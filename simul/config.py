"""模拟宇宙配置模块."""

from __future__ import annotations

from typing import List

from utils.common.config_base import ConfigBase


class Config(ConfigBase):
    """模拟宇宙配置类.

    继承自 ConfigBase,添加模拟宇宙特有的配置项.

    Attributes:
        order_text (str): 命途优先级顺序
        fate (str): 当前命途
        fates (list): 所有命途列表
        map_sha (str): 地图哈希值
        show_map_mode (int): 显示地图模式
        debug_mode (int): 调试模式
        speed_mode (int): 速度模式
        use_consumable (int): 是否使用消耗品
        slow_mode (int): 慢速模式
        force_update (int): 强制更新
        unlock (int): 解锁状态
        bonus (int): 奖励模式
    """

    def __init__(self):
        """初始化模拟宇宙配置."""
        super().__init__()

        # ===== 模拟宇宙特有配置 =====
        self.order_text = "1 2 3 4"
        self.fate = "巡猎"
        self.fates = ["存护", "记忆", "虚无", "丰饶", "巡猎", "毁灭", "欢愉", "繁育", "智识"]
        self.map_sha = ""

        # 模式开关
        self.show_map_mode = 0
        self.debug_mode = 0
        self.speed_mode = 0
        self.use_consumable = 0
        self.slow_mode = 0
        self.force_update = 0
        self.unlock = 0
        self.bonus = 0

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
            self.read_key_mapping(data)

            # 读取模拟宇宙特有配置
            try:
                order_value = config_data.get('order_text')
                if isinstance(order_value, list):
                    self.order_text = " ".join(str(x) for x in order_value)

                self.fate = str(config_data.get('fate', self.fate))
                self.map_sha = str(config_data.get('map_sha', self.map_sha))
                self.show_map_mode = int(config_data.get('show_map_mode', self.show_map_mode) or 0)
                self.debug_mode = int(config_data.get('debug_mode', self.debug_mode) or 0)
                self.speed_mode = int(config_data.get('speed_mode', self.speed_mode) or 0)
                self.bonus = int(config_data.get('bonus', self.bonus) or 0)
                self.use_consumable = int(config_data.get('use_consumable', self.use_consumable) or 0)
                self.force_update = int(config_data.get('force_update', self.force_update) or 0)
                self.slow_mode = int(config_data.get('slow_mode', self.slow_mode) or 0)
            except (KeyError, ValueError, TypeError):
                pass
        else:
            self.save()

    def save(self):
        """保存配置文件."""
        # 尝试保留已有的 secondary_fate 和 prior 配置
        existing_data = self.load_yaml()

        secondary_fate = ['巡猎', '毁灭', '丰饶']
        prior = self._get_default_prior()

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
                "show_map_mode": self.show_map_mode,
                "debug_mode": self.debug_mode,
                "speed_mode": self.speed_mode,
                "bonus": self.bonus,
                "long_press_sprint": self.long_press_sprint,
                "use_consumable": self.use_consumable,
                "slow_mode": self.slow_mode,
                "force_update": self.force_update,
                "timezone": self.timezone,
            },
            "prior": prior,
            "key_mapping": self.mapping
        })

    def _get_default_prior(self) -> dict:
        """获取默认的优先级配置.

        Returns:
            默认优先级字典
        """
        return {
            '奇物':
                ['福灵胶', '博士之袍', '陨石球', '降维骰子', '信仰债券', '时空棱镜', '朋克洛德', '香涎干酪',
                 '龋齿星系'],
            '事件':
                ['购买一个', '丢下雕像', '和序列扑满玩', '信仰星神', '克里珀的恩赐', '哈克的藏品', '动作片',
                 '感恩克里珀星神', '换取1个星祝福', '星神的记载', '翻开牌', '摧毁黑匣', '1个1星祝福',
                 '1个1-星祝福', '选择里奥'],
            '存护':
                ['零维强化', '均晶转变', '共晶反应', '宏观偏析', '超静定场', '谐振传递', '四棱锥体',
                 '聚塑', '哨戒', '亚共晶体', '切变结构', '弥合', '迸裂晶格'],
            '记忆':
                ['体验的富翁', '全面记忆', '第二次初恋', '浮黎', '缄默', '纯真', '难言的羞耻',
                 '怅然若失', '麻木不仁', '不寒而栗', '特立独行', '头晕目眩', '多愁善感', '沦浃肌髓'],
            '虚无':
                ['局外人', '苦难与阳光', '怀疑的四重根', '为何一切尚未消失', '感官追奉者的葬礼',
                 '被装在套子里的人', '旷野的呼告', '存在的黄昏', '火堆外的夜', '知觉迷墙', '虚妄贡品',
                 '日出之前', '无根据颂歌', '自欺咖啡馆', '他人即地狱', '开端与终结'],
            '丰饶':
                ['诸行无常', '诸法无我', '一法界心', '施诸愿印', '延彼遐龄', '厌离邪秽苦',
                 '天人不动众', '宝光烛日月', '明澈琉璃身', '法雨', '胜军', '灭罪累生善'],
            '巡猎':
                ['柘弓危矢', '射不主皮', '帝星君临', '白矢决射御', '云镝逐步离', '彤弓素矰',
                 '背孤击虚'],
            '毁灭':
                ['激变变星', '极端氦闪', '事件视界', '寰宇热寂特征数', '反物质非逆方程', '戒律性闪变',
                 '危害性余光', '毁灭性吸积', '原生黑洞', '轨道红移', '预兆性景深', '递增性末日',
                 '灾难性共振', '破坏性耀发', '偏振受体', '永坍缩体', '不稳定带', '哨戒卫星',
                 '回光效应'],
            '欢愉':
                ['末日狂欢', '开盖有奖', '茫茫白夜', '众生安眠', '阴风阵阵', '被涂污的信天翁',
                 '十二猴子与怒汉', '操行满分', '基本有害', '灰暗的火', '第二十一条军规',
                 '流吧你的眼泪'],
            '繁育':
                ['刺吸口器', '结晶鳌刺', '酚类物质', '子囊释放', '菌种脓疤', '镰刀肢足', '腐殖疮', '裂解酶',
                 '代谢腔', '裸脑质', '代谢腔', '催化剂', '节间膜', '孢夹', '骨刃', '鳞翅', '脊刺', '槽针',
                 '液囊'],
            '智识':
                ['34型灰质', '2型杏仁核', '18型枕叶', '前庭系统', '递质合成', '外显记忆', '触觉通路',
                 '阈下知觉', '纹状皮层', '跳跃传导', '齿轮啮合的王座', '导线弯绕的指环', '能量变距的权杖',
                 '偏时引燃的炬火', '延迟衍射的烛光', '金属斑驳的华盖', '管道交错的桂冠', '线圈编制的罗琦']
        }


config = Config()
