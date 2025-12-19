"""差分宇宙自动化核心实现.

该模块实现差分宇宙的完整自动化流程,包括区域导航,事件处理,
祝福选择,战斗触发等功能.

Classes:
    DivergentUniverse: 差分宇宙自动化控制器
"""

from __future__ import annotations

# ===== 第三方库 =====
import bisect

# ===== 标准库 =====
import time
import traceback
from collections import defaultdict
from typing import TYPE_CHECKING

import cv2 as cv
import diver.keyops as keyops
import keyboard
import numpy as np
import pyautogui
import win32api
import win32con
import win32gui

# ===== 本项目模块 =====
from align_angle import main as align_angle
from diver.action_engine import ActionEngine
from diver.config import config
from diver.handlers.area_basic_handler import (
    handle_plane_area,
    handle_rest_area,
    handle_shop_area,
    handle_wealth_area,
)
from diver.handlers.area_combat_handler import handle_battle_area, handle_boss_area
from diver.handlers.area_route_handler import handle_event_reward_encounter
from diver.handlers.event_handler import (
    align_event as align_event_handler,
    find_event_text as find_event_text_handler,
    handle_event,
)
from diver.handlers.popup_handler import check_pop as check_pop_handler
from diver.handlers.selection_handler import (
    handle_blessing,
    handle_boon,
    handle_curio,
    handle_drop_blessing,
    handle_equation,
    handle_weighted_curio,
)
from diver.handlers.team_handler import (
    detect_team_members,
    prepare_active_character,
    sync_team_state_and_long_range,
)
from diver.keyops import KeyController
from diver.scoring import (
    build_blessing_prior,
    build_boon_prior,
    build_curio_prior,
    build_equation_prior,
    build_other_prior,
    build_weighted_curio_prior,
    score_blessing,
    score_boon,
    score_curio,
    score_equation,
    score_event_choice,
    score_other,
    score_weighted_curio,
)
from diver.text_utils import (
    clean_text as clean_text_fn,
    get_text_type as get_text_type_fn,
    merge_text as merge_text_fn,
)
from diver.utils import notif, set_forground, UniverseUtils
from utils.common import team_utils
from utils.common.json_utils import (
    read_actions_json,
    read_global_prior,
    read_team_prior,
)
from utils.common.run_counter import update_weekly_counter
from utils.log import log, my_print as print, print_exc

# 类型检查时的导入
if TYPE_CHECKING:
    from typing import Any, Callable

# 版本号
version = "v8.042"


class DivergentUniverse(UniverseUtils):
    """差分宇宙自动化控制器.

    该类继承自 UniverseUtils,实现差分宇宙的完整自动化流程,包括:
    - 区域导航和传送门识别
    - 事件处理和选项选择
    - 祝福选择策略
    - 战斗触发和队伍管理
    - 状态监控和异常恢复

    Attributes:
        is_need_detect_team (bool): 是否需要检测队伍成员(首次进入时为 True)
        team_detect (dict): 队伍成员检测缓存
        _stop (bool): 停止运行标志
        current_floor (int): 当前楼层(0-12)
        allow_skill (bool): 是否允许使用秘技(消耗品不足时禁用)
        total_count (int): 总通关计数
        session_count (int): 本次会话通关计数
        init_timestamp (float): 初始化时间戳
        current_area (str): 当前区域类型
        action_history (list): 最近执行的动作历史
        event_priorities (dict): 事件选项优先级配置
        character_priorities (dict): 角色祝福优先级配置
        all_blessings (dict): 所有祝福信息
        blessing_priorities (defaultdict): 当前祝福优先级表
        team_members (dict): 队伍成员信息
        ocr_time_history (list): OCR 识别耗时历史
        last_fail_timestamp (float): 上次失败时间戳
        last_action_timestamp (float): 上次动作时间戳
        is_huangquan_mode (bool): 是否启用黄泉模式(特殊角色优化)
        is_daheta_enabled (bool): 是否启用大黑塔角色
        is_daheta_skill_active (bool): 大黑塔秘技是否生效中
        is_baie_enabled (bool): 是否启用白厄模式
        current_event_text (str): 当前事件文本
        ranged_character_slot (str): 远程角色所在槽位
        is_boss_counted (bool): 当前首领房是否已计入统计
    """

    def __init__(self):
        """初始化差分宇宙控制器."""
        super().__init__()

        # ===== 队伍检测状态 =====
        self.is_need_detect_team = True  # 首次进入差分宇宙后需要获取队伍成员
        self.team_detect = {}  # 队伍成员检测缓存

        # ===== 运行控制状态 =====
        self._stop = True  # 停止标志
        self.floor = 0  # 当前楼层

        # ===== 秘技控制 =====
        # 允许使用秘技,当消耗品不足时设为 False
        self.allow_e = 1

        # ===== 计数器 =====
        self.count = 0  # 总通关计数
        self.my_cnt = 0  # 本次会话通关计数
        self.init_tm = time.time()  # 初始化时间戳

        # ===== 区域和动作状态 =====
        self.area_now = None  # 当前区域类型
        self.action_history = []  # 最近执行的动作历史(保留最近 10 条)

        # ===== 配置数据加载 =====
        self.event_prior = self.read_json("actions/event.json", name="event")
        self.character_prior = self.read_json(
            "actions/character_prior.json", name="char"
        )
        self.all_blessing = self.read_json("actions/blessing.json", name="blessing")
        self.global_prior = read_global_prior("actions/global_prior.json")
        self.team_prior = read_team_prior("actions/team_prior.json")
        # 六个独立的优先级表
        self.blessing_prior = defaultdict(int)  # 普通祝福优先级表
        self.equation_prior = defaultdict(int)  # 方程选择优先级表
        self.boon_prior = defaultdict(int)  # 金血祝福优先级表
        self.curio_prior = defaultdict(int)  # 奇物优先级表
        self.weighted_curio_prior = defaultdict(int)  # 加权奇物优先级表
        self.other_prior = defaultdict(int)  # 其他 (fallback) 优先级表

        # ===== 队伍状态 =====
        self.team_member = {}  # 队伍成员信息 {名称: 槽位}

        # ===== 性能监控 =====
        self.ocr_time_list = [0.5]  # OCR 识别耗时历史
        self.fail_tm = 0  # 上次失败时间戳
        self.last_action_time = 0  # 上次动作时间戳

        # ===== 特殊角色优化 =====
        # 黄泉角色优化:启用后使用特殊的战斗触发逻辑
        self.quan = 0

        # 大黑塔角色优化:优先级高于黄泉
        self.da_hei_ta = False  # 是否启用
        self.da_hei_ta_effecting = False  # 秘技是否生效中(进战后清除)

        # 白厄模式
        self.bai_e = 0

        # ===== 事件处理 =====
        self.event_text = ""  # 当前事件文本

        # ===== 战斗配置 =====
        self.long_range = config.default_long_range_slot  # 远程角色槽位,默认从 config 读取

        # ===== 首领房统计 =====
        self.boss_counted = False  # 当前首领房是否已计入统计

        # ===== 初始化 =====
        self.init_floor()
        self.default_json_path = "actions/default.json"
        self.action_engine = ActionEngine(self)
        self.default_json = self.action_engine.load_actions(self.default_json_path)
        pyautogui.FAILSAFE = False
        self.update_count()
        notif("开始运行", f"初始计数:{self.count}")

    def route(self):
        self.threshold = config.default_threshold
        self.is_get_team = True  # 启动后重置状态
        while True:
            if self._stop:
                break
            hwnd = win32gui.GetForegroundWindow()  # 根据当前活动窗口获取句柄
            Text = win32gui.GetWindowText(hwnd)
            warn_game = False
            cnt = 0
            while Text != "崩坏：星穹铁道" and Text != "云.星穹铁道" and not self._stop:
                self.lst_changed = time.time()
                if self._stop:
                    raise KeyboardInterrupt
                if not warn_game:
                    warn_game = True
                    log.warning(f"等待游戏窗口,当前窗口:{Text}")
                time.sleep(0.5)
                cnt += 1
                if cnt == 1200:
                    set_forground()
                hwnd = win32gui.GetForegroundWindow()  # 根据当前活动窗口获取句柄
                Text = win32gui.GetWindowText(hwnd)
            if self._stop:
                break
            self.loop()
        log.info("停止运行")

    def loop(self):
        tm_loop_start = time.time()
        self.ts.forward(self.get_screen())
        tm_forward = time.time()
        res = self.run_static()
        tm_static = time.time()
        log.debug(
            f"loop 耗时: forward={int((tm_forward-tm_loop_start)*1000)}ms, static={int((tm_static-tm_forward)*1000)}ms"
        )
        if res == "":
            area_text = self.clean_text(
                self.ts.ocr_one_row(self.screen, [50, 350, 3, 35]), char=0
            )
            if "位面" in area_text or "区域" in area_text or "第" in area_text:
                self.area()
                self.last_action_time = time.time()

            elif self.check("c", 0.988, 0.1028, threshold=0.925):
                # 未检查到自动战斗,已经入站,清除秘技持续
                self.da_hei_ta_effecting = False
                self.press("v")
            else:
                text = self.merge_text(
                    self.ts.find_with_box([400, 1920, 100, 600], redundancy=0)
                )
                if time.time() - self.last_action_time > 60:
                    self.click((0.5, 0.1))
                    self.click((0.5, 0.25))
                    self.last_action_time = time.time()
        else:
            self.last_action_time = time.time()

    def do_action(self, action) -> int:
        """委托给 ActionEngine 执行动作."""
        return self.action_engine.do_action(action)

    def load_actions(self, json_path):
        """加载动作配置文件."""
        return self.action_engine.load_actions(json_path)

    def run_static(
        self, json_path=None, json_file=None, action_list=[], skip_check=0
    ) -> str:
        """执行静态规则匹配."""
        name = self.action_engine.run_static(
            json_file=json_file,
            json_path=json_path,
            action_list=action_list,
            skip_check=skip_check,
            merge_text_fn=self.merge_text,
        )
        if name:
            self.action_history.append(name)
            self.action_history = self.action_history[-10:]
        return name

    def select_difficulty(self):
        time.sleep(0.5)
        self.click_position([125, 175 + int((self.diffi - 1) * (605 - 175) / 4)])

    def read_json(self, file_path, name):
        """读取 actions JSON 并返回结构化数据."""

        return read_actions_json(file_path, name)

    def clean_text(self, text, char=1):
        """清洗 OCR 文本."""
        return clean_text_fn(text, char=char)

    def merge_text(self, text, char=1):
        """合并 OCR 结果并清洗."""
        return merge_text_fn(self.ts, text, char=char)

    def init_floor(self):
        self.portal_cnt = 0
        self.area_state = 0
        self.event_solved = 0
        self.blessing_solved = 0
        self.fail_cnt = 0
        self.now_event = ""
        if hasattr(self, "keys"):
            self.keys.fff = 0
        for i in ["w", "a", "s", "d", "f"]:
            keyops.keyUp(i)

    def close_and_exit(self, click=True):
        self.press("esc")
        time.sleep(2.5)
        self.init_floor()
        if not click:
            if time.time() - self.fail_tm < 90:
                click = True
                self.fail_tm = 0
            else:
                self.fail_tm = time.time()
        if click:
            self.floor = 0
            self.click_position([1530, 990])
            time.sleep(1)

    def get_text_type(self, text, types, prefix=1):
        """通过前缀匹配识别文本类型."""
        return get_text_type_fn(text, types, prefix=prefix)

    def has_team_member(self, char_name):
        """检查队伍中是否有指定角色."""
        return team_utils.has_team_member(self.team_member, char_name)

    def get_team_member_position(self, char_name):
        """获取队伍中指定角色的位置."""
        return team_utils.get_team_member_position(self.team_member, char_name)

    def find_team_member(self):
        return detect_team_members(self)

    def get_now_area(self, deep=0):
        tm_start = time.time()
        team_member = self.find_team_member()
        tm_team = time.time()
        self.area_text = self.clean_text(
            self.ts.ocr_one_row(self.screen, [50, 350, 3, 35]), char=0
        )
        tm_ocr = time.time()
        print("area_text:", self.area_text, "deep:", deep)
        log.debug(
            f"get_now_area 耗时: team={int((tm_team-tm_start)*1000)}ms, ocr={int((tm_ocr-tm_team)*1000)}ms"
        )
        if (
            "位面" in self.area_text
            or "区域" in self.area_text
            or "第" in self.area_text
        ):
            # 同步队伍状态(只在首次识别时会有变化)
            sync_team_state_and_long_range(self, team_member)

            res = self.get_text_type(
                self.area_text,
                [
                    "事件",
                    "奖励",
                    "遭遇",
                    "商店",
                    "首领",
                    "战斗",
                    "财富",
                    "休整",
                    "位面",
                ],
            )
            if (res == "位面" or res is None) and deep == 0:
                self.mouse_move(20)
                scr = self.screen
                time.sleep(0.3)
                self.get_screen()
                self.mouse_move(-20)
                res = self.get_now_area(deep=1)
                self.screen = scr
            return res
        else:
            return None

    def find_portal(self, type=None):
        prefer_portal = {
            "奖励": 3,
            "事件": 3,
            "战斗": 2,
            "遭遇": 2,
            "商店": 1,
            "财富": 1,
        }
        if config.enable_portal_prior:
            prefer_portal.update(config.portal_prior)
        prefer_portal.update({"首领": 4, "休整": 4})
        tm = time.time()
        text = self.ts.find_with_box([0, 1920, 0, 540], forward=1, mode=2)
        tm_ocr = time.time()
        log.debug(f"find_portal OCR 耗时: {int((tm_ocr-tm)*1000)}ms")
        portal = {"score": 0, "nums": 0, "type": ""}
        for i in text:
            if ("区" in i["raw_text"] or "域" in i["raw_text"]) and (
                i["box"][0] > 400 or i["box"][2] > 60
            ):
                portal_type = self.get_text_type(i["raw_text"], prefer_portal)
                if "冒" in i["raw_text"] or "险" in i["raw_text"]:
                    portal["nums"] += 1
                elif portal_type is not None:
                    i.update(
                        {
                            "score": prefer_portal[portal_type]
                            + 10 * (portal_type == type),
                            "type": portal_type,
                            "nums": portal["nums"] + 1,
                        }
                    )
                    if i["score"] > portal["score"]:
                        portal = i
                    else:
                        portal["nums"] = i["nums"]
        ocr_time = time.time() - tm
        self.ocr_time_list = self.ocr_time_list[-5:] + [ocr_time]
        print(f"识别时间:{int(ocr_time*1000)}ms", text, portal)
        return portal

    def sleep(self, tm=2):
        time.sleep(tm)
        self.ts.forward(self.get_screen())

    def portal_bias(self, portal):
        return (portal["box"][0] + portal["box"][1]) // 2 - 950

    def aim_portal(self, portal):
        zero = bisect.bisect_left(config.angles, 0)
        while abs(self.portal_bias(portal)) > 50:
            angle = bisect.bisect_left(config.angles, self.portal_bias(portal)) - zero
            self.mouse_move(angle)
            if abs(self.portal_bias(portal)) < 200:
                return portal
            time.sleep(0.2)
            portal_after = self.find_portal(portal["type"])
            if portal_after["score"] == 0:
                self.press("w", 1)
                portal_after = self.find_portal(portal["type"])
                if portal_after["score"] == 0:
                    return portal
            portal = portal_after
        return portal

    def forward_until(self, text_list=[], timeout=5, moving=0, chaos=0):
        tm = time.time()
        if not moving:
            keyops.keyDown("w")
        while time.time() - tm < timeout:
            self.get_screen()
            if self.check_f(check_text=0):
                keyops.keyUp("w")
                print(text_list)
                if chaos:
                    if self.check_f(is_in=["混沌", "战利品"]):
                        self.press("f")
                        for _ in range(1):
                            self.press("s", 0.2)
                            self.press("f")
                        time.sleep(0.8)
                        tmm = time.time()
                        while time.time() - tmm < 8:
                            self.ts.forward(self.get_screen())
                            area_text = self.clean_text(
                                self.ts.ocr_one_row(self.screen, [50, 350, 3, 35]),
                                char=0,
                            )
                            if (
                                "位面" in area_text
                                or "区域" in area_text
                                or "第" in area_text
                            ):
                                break
                            self.run_static()
                        time.sleep(0.6)
                        tm = time.time()
                        keyops.keyDown("w")
                if self.check_f(is_in=text_list):
                    self.press("f")
                    for _ in range(1):
                        self.press("s", 0.2)
                        self.press("f")
                    return 1
                else:
                    tm += 0.7
                    keyops.keyDown("w")
                    time.sleep(0.5)
        keyops.keyUp("w")
        return 0

    def portal_opening_days(self, aimed=0, static=0, deep=0):
        """寻找并进入传送门."""
        if deep > 1:
            self.close_and_exit(click=self.fail_count > 1)
            self.fail_count += 1
            return
        if deep == 0:
            self.portal_cnt += 1
        portal = {"score": 0, "nums": 0, "type": ""}
        moving = 0
        if static:
            angles = [0, 90, 90, 90, 45, -90, -90, -90, -45]
            for i, angle in enumerate(angles):
                self.mouse_move(angle)
                time.sleep(0.2)
                portal = self.find_portal()
                if portal["score"]:
                    break
            if self.floor in [1, 2, 4, 5, 6, 7, 9, 10]:
                if portal["nums"] == 1 and portal["score"] < 2:
                    portal_pre = portal
                    portal_type = portal["type"]
                    bias = 0
                    for i in range(i + 1, len(angles)):
                        self.mouse_move(angles[i])
                        bias += angles[i]
                        time.sleep(0.2)
                        portal_after = self.find_portal()
                        if (
                            portal_after["score"]
                            and portal_type != portal_after["type"]
                        ):
                            portal = portal_after
                            break
                    if portal["type"] == portal_type:
                        portal = portal_pre
                        self.mouse_move(-bias)
        tm = time.time()
        while time.time() - tm < 5 + 2 * (portal["score"] != 0):
            if aimed == 0:
                if portal["score"] == 0:
                    portal = self.find_portal()
            else:
                if self.forward_until(
                    [portal["type"]] if portal["score"] else ["区域", "结束", "退出"],
                    timeout=2.5,
                    moving=moving,
                ):
                    self.init_floor()
                    return
                else:
                    keyops.keyUp("w")
                    moving = 0
                    self.press("d", 0.6)
                    self.portal_opening_days(aimed=0, static=1, deep=deep + 1)
                    return
            if portal["score"] and not aimed:
                if moving:
                    print("stop moving")
                    keyops.keyUp("w")
                    moving = 0
                    self.press("s", min(max(self.ocr_time_list), 0.4))
                    continue
                else:
                    print("aiming...")
                    tmp_portal = self.aim_portal(portal)
                    if tmp_portal["score"] == 0:
                        self.portal_opening_days(aimed=0, static=1, deep=deep + 1)
                        return
                    else:
                        portal = tmp_portal
                        aimed = 1
                    moving = 1
                    keyops.keyDown("w")
            elif portal["score"] == 0:
                if not moving:
                    keyops.keyDown("w")
                    moving = 1
        if moving:
            keyops.keyUp("w")

    def event_score(self, text, event):
        """计算事件选项得分."""
        return score_event_choice(text, event)

    def event(self):
        handle_event(self)

    def find_event_text(self):
        return find_event_text_handler(self)

    def check_pop(self, *args, **kwargs):
        check_pop_handler(self, *args, **kwargs)

    def align_event(self, key, deep=0, event_text=None, click=0):
        align_event_handler(self, key, deep=deep, event_text=event_text, click=click)

    def skill(self, quan=0):
        if not self.allow_e:
            return
        self.press("e")
        time.sleep(0.4)
        self.get_screen()
        if self.check("e", 0.4995, 0.7500):
            self.solve_snack()
            if quan and self.allow_e:
                time.sleep(0.4)
            else:
                time.sleep(1.5 * self.allow_e)

    def check_dead(self):
        self.get_screen()
        if self.check("divergent/sile", 0.5010, 0.7519, threshold=0.96):
            self.click_position([1188, 813])
            time.sleep(2.5)

    def area(self):
        tm_area_start = time.time()
        area_now = self.get_now_area()
        tm_first_detect = time.time()
        time.sleep(0.5)
        if self.get_now_area() != area_now or area_now is None:
            return 0
        tm_second_detect = time.time()
        log.debug(
            f"area 识别耗时: first={int((tm_first_detect-tm_area_start)*1000)}ms, second={int((tm_second_detect-tm_first_detect)*1000)}ms"
        )
        if self.area_state == -1:
            self.close_and_exit(click=False)
            return 1
        now_floor = self.floor
        for i in range(1, 14):
            if f"{i}13" in self.area_text:
                now_floor = i
        if now_floor != self.floor:
            if now_floor < self.floor:
                self.init_floor()
            self.floor = now_floor
            if self.floor in [5, 10]:
                time.sleep(3)
        time.sleep(0.8)

        if self.area_state == 0 and area_now != "首领":
            prepare_active_character(self, area_now)

        self.get_screen()
        if self.check("divergent/arrow", 0.7833, 0.9231, threshold=0.95):
            keyops.keyDown("alt")
            time.sleep(0.2)
            self.click_position([413, 79])
            keyops.keyUp("alt")
        time.sleep(0.7)

        self.check_dead()

        if area_now is not None:
            self.area_now = area_now
        else:
            area_now = self.area_now

        if self.portal_cnt > 1:
            # 这里考虑的是全局异常暂离次数达到2次,就结束本次探索,或许可以考虑改为单个区域
            self.close_and_exit(click=False)
            return 1

        log.info(
            f"floor:{self.floor}, state:{self.area_state}, area:{area_now}, text:{self.area_text}"
        )

        if area_now in ["事件", "奖励", "遭遇"]:
            result = handle_event_reward_encounter(self)
            if result is not None:
                return result

        elif area_now == "休整":
            handle_rest_area(self)

        elif area_now == "商店":
            handle_shop_area(self)

        elif area_now == "首领":
            result = handle_boss_area(self)
            if result is not None:
                return result

        elif area_now == "战斗":
            handle_battle_area(self)

        elif area_now == "财富":
            handle_wealth_area(self)

        elif area_now == "位面":
            handle_plane_area(self)
        else:
            self.press("F4")
        return 1

    def update_blessing_prior(self):
        """更新普通祝福优先级表."""
        self.blessing_prior = build_blessing_prior(
            team_member_names=list(self.team_member),
            character_prior=self.character_prior,
            team_type=config.team,
            team_prior=self.team_prior,
            global_prior=self.global_prior,
        )

    def update_equation_prior(self):
        """更新方程选择优先级表."""
        self.equation_prior = build_equation_prior(
            team_member_names=list(self.team_member),
            character_prior=self.character_prior,
            team_type=config.team,
            team_prior=self.team_prior,
            global_prior=self.global_prior,
        )

    def update_boon_prior(self):
        """更新金血祝福优先级表."""
        self.boon_prior = build_boon_prior(
            team_member_names=list(self.team_member),
            character_prior=self.character_prior,
            team_type=config.team,
            team_prior=self.team_prior,
            global_prior=self.global_prior,
        )

    def update_curio_prior(self):
        """更新奇物优先级表."""
        self.curio_prior = build_curio_prior(
            team_member_names=list(self.team_member),
            character_prior=self.character_prior,
            team_type=config.team,
            team_prior=self.team_prior,
            global_prior=self.global_prior,
        )

    def update_weighted_curio_prior(self):
        """更新加权奇物优先级表."""
        self.weighted_curio_prior = build_weighted_curio_prior(
            team_member_names=list(self.team_member),
            character_prior=self.character_prior,
            team_type=config.team,
            team_prior=self.team_prior,
            global_prior=self.global_prior,
        )

    def update_other_prior(self):
        """更新其他 (fallback) 优先级表."""
        self.other_prior = build_other_prior(
            team_member_names=list(self.team_member),
            character_prior=self.character_prior,
            team_type=config.team,
            team_prior=self.team_prior,
            global_prior=self.global_prior,
        )

    def blessing_score(self, text):
        """计算普通祝福得分."""
        return score_blessing(text, self.blessing_prior, self.all_blessing)

    def equation_score(self, text):
        """计算方程选择得分."""
        return score_equation(text, self.equation_prior)

    def boon_score(self, text):
        """计算金血祝福得分."""
        return score_boon(text, self.boon_prior)

    def curio_score(self, text):
        """计算奇物得分."""
        return score_curio(text, self.curio_prior)

    def weighted_curio_score(self, text):
        """计算加权奇物得分."""
        return score_weighted_curio(text, self.weighted_curio_prior)

    def other_score(self, text):
        """计算其他 (fallback) 得分."""
        return score_other(text, self.other_prior)

    def drop_blessing(self):
        """丢弃祝福 (选分数最低的)."""
        handle_drop_blessing(self)

    def boon(self):
        """选择金血祝福."""
        handle_boon(self)

    def blessing(self, reverse=1, boon=0):
        """处理普通祝福选择."""
        handle_blessing(self, reverse=reverse, boon=boon)

    def equation(self):
        """处理方程选择."""
        handle_equation(self)

    def curio(self):
        """处理奇物选择."""
        handle_curio(self)

    def weighted_curio(self):
        """处理加权奇物选择."""
        handle_weighted_curio(self)

    def end_of_uni(self):
        self.floor = 0
        self.init_floor()

    def save_or_exit(self):
        """探索结束时点击返回主界面按钮."""
        time.sleep(0.5)
        self.ts.forward(self.get_screen())
        if not self.click_text("返回主界面"):
            # 如果 OCR 未识别到,回退到坐标点击
            self.click_position([740, 973])

    def add_count_and_notify(self):
        """增加计数并通知"""
        self.update_count(0)
        self.my_cnt += 1
        notif(
            "已完成",
            f"本次第 {self.my_cnt} 轮",
            cnt=str(self.count),
        )

    def update_count(self, read=True):
        """读取/更新通关计数(按配置时区在每周一 04:00 刷新)."""

        self.count, self.count_tm = update_weekly_counter(
            file_name="logs/notif.txt",
            timezone=config.timezone,
            read_mode=bool(read),
            current_count=int(getattr(self, "count", 0)),
            current_count_tm=float(getattr(self, "count_tm", 0.0)),
        )

    def stop(self, *_, **__):
        """停止运行.

        安全地停止自动化流程,重置楼层状态.
        """
        log.info("尝试停止运行")
        try:
            self.init_floor()
        except Exception as e:
            # 停止过程中的异常不应阻止停止操作
            log.debug(f"停止时重置楼层状态失败: {e}")
        self._stop = True

    def on_key_press(self, event):
        """F8 按键回调处理.

        Args:
            event: 按键事件对象
        """
        if event.name == "f8":
            print("F8 已被按下,尝试停止运行")
            self.stop()

    def start(self):
        """启动自动化流程.

        注册热键监听,启动主循环,并处理各类异常.
        """
        log.info(f"当前队伍类型: {config.team}")
        self._stop = False
        keyboard.on_press(self.on_key_press)
        self.keys = KeyController(self)
        try:
            self.route()
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            log.info("用户终止进程")
            if not self._stop:
                self.stop()
        except Exception as e:
            print_exc()
            traceback.print_exc()
            log.info(str(e))
            log.info("发生错误,尝试停止运行")
            self.stop()

    def screen_test(self):
        cv.imshow("screen", self.get_screen())
        cv.waitKey(0)
