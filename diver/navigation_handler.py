"""寻路处理模块.

该模块负责:
- 大地图寻路逻辑
- 目标点导航
- 路径障碍处理
"""

from __future__ import annotations

import math
import random
import threading
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Callable

import pyautogui

if TYPE_CHECKING:
    pass


def normalize_angle(angle: float) -> float:
    """将角度归一化到 [-180, 180] 范围.

    Args:
        angle: 原始角度

    Returns:
        归一化后的角度
    """
    while angle < -180:
        angle += 360
    while angle > 180:
        angle -= 360
    return angle


def calculate_target_angle(current_loc: tuple, target_loc: tuple) -> float:
    """计算从当前位置到目标位置的角度.

    Args:
        current_loc: 当前位置 (x, y)
        target_loc: 目标位置 (x, y)

    Returns:
        方向角度(度)
    """
    return (
        math.atan2(
            target_loc[0] - current_loc[0],
            target_loc[1] - current_loc[1],
        )
        / math.pi
        * 180
    )


def init_navigation(universe) -> tuple:
    """初始化导航状态.

    准备寻路所需的初始状态和地图数据.

    Args:
        universe: UniverseUtils 实例

    Returns:
        (bw_map, local_screen, shape) 或 None 如果初始化失败
    """
    shape = (int(universe.scx * 190), int(universe.scx * 190))
    bw_map = universe.get_bw_map(gs=0)
    universe.loc_off = 0

    # 初始定位
    universe.get_loc(bw_map, rg=40 - universe.find * 10)

    if universe.find == 1:
        universe.press("w", 0.2)

    universe.get_screen()
    local_screen = universe.get_local(0.9333, 0.8657, shape)

    return bw_map, local_screen, shape


def handle_recording_mode(universe, bw_map) -> None:
    """处理录图模式.

    在录图模式下,将小地图数据覆盖到大地图中.

    Args:
        universe: UniverseUtils 实例
        bw_map: 黑白格式的小地图
    """
    universe.write_map(bw_map)
    universe.get_map()


def check_immediate_interaction(universe, log) -> bool:
    """检查是否可以立即交互.

    如果当前就在交互点上,清理目标并返回.

    Args:
        universe: UniverseUtils 实例
        log: 日志记录器

    Returns:
        True 如果已处理交互,应该返回
    """
    if universe.goodf() and not universe.ts.sim("黑塔"):
        for j in deepcopy(universe.target):
            if j[1] == 2:
                universe.target.remove(j)
                log.info("removed:" + str(j))
        return True
    return False


def start_movement(universe, keyops, target_type: int) -> int:
    """开始移动.

    初始化移动状态并开始前进.

    Args:
        universe: UniverseUtils 实例
        keyops: 按键操作模块
        target_type: 目标类型

    Returns:
        是否已使用冲刺 (1=是, 0=否)
    """
    if universe._stop == 0:
        keyops.keyDown("w")

    time.sleep(0.25)
    sprint_used = 0

    if target_type != 3:
        universe.sprint()
        sprint_used = 1

    time.sleep(0.25)
    return sprint_used


def try_avoid_obstacle(universe, keyops, log, retry_count: int) -> tuple:
    """尝试绕过障碍物.

    当检测到移动卡住时,尝试通过左右移动绕过障碍.

    Args:
        universe: UniverseUtils 实例
        keyops: 按键操作模块
        log: 日志记录器
        retry_count: 剩余重试次数

    Returns:
        (是否成功, 新的重试次数)
    """
    directions = " da"  # 空格、d、a

    if retry_count > 0:
        keyops.keyUp("w")
        universe.press("s", 0.35)
        universe.press(directions[retry_count], 0.2 * random.randint(1, 3))
        universe.press("w", 0.3)

        # 启动保持移动的线程
        universe.move = 1
        universe.get_screen()
        threading.Thread(target=universe.keep_move).start()

        bw_map = universe.get_bw_map(gs=0)
        universe.get_loc(bw_map, rg=28, fbw=1)
        universe.get_real_loc()
        universe.move = 0

        time.sleep(0.12)
        universe.sprint()

        return True, retry_count - 1
    else:
        keyops.keyUp("w")
        return False, 0


def handle_waypoint_reached(universe, log, loc, target_type: int) -> tuple:
    """处理到达路径点.

    当到达中间路径点时,移除该点并获取下一个目标.

    Args:
        universe: UniverseUtils 实例
        log: 日志记录器
        loc: 当前目标位置
        target_type: 目标类型

    Returns:
        (新的目标位置, 新的目标类型)
    """
    universe.target.remove((loc, target_type))
    log.info("removed:" + str((loc, target_type)))
    universe.lst_changed = time.time()
    return universe.get_tar()


def handle_teleport_check(universe, keyops, log, target_type: int) -> bool:
    """检查并处理传送点.

    Args:
        universe: UniverseUtils 实例
        keyops: 按键操作模块
        log: 日志记录器
        target_type: 目标类型

    Returns:
        True 如果成功传送,应该返回
    """
    universe.get_screen()

    if target_type == 3 and universe.check(
        "f", 0.4443, 0.4417, mask="mask_f1", threshold=0.96
    ):
        universe.press("f")
        keyops.keyUp("w")

        if universe.nof(must_be="tp"):
            log.info("大图识别到传送点!")
            return True

    elif (target_type != 3 and universe.goodf()) or not universe.isrun():
        keyops.keyUp("w")
        return True

    return False


def handle_target_type_1(universe, keyops) -> None:
    """处理目标类型 1 的后续操作.

    目标类型 1 通常是战斗点,需要特殊的攻击序列.

    Args:
        universe: UniverseUtils 实例
        keyops: 按键操作模块
    """
    if not universe.quan:
        # 普通模式:执行攻击序列
        if universe._stop == 0:
            pyautogui.click()
        time.sleep(1.1)

        universe.press("s")

        if universe._stop == 0:
            pyautogui.click()
        time.sleep(0.8)

        # 如果目标点较少,执行更多攻击
        if len(universe.target) <= 2:
            time.sleep(0.3)
            universe.press("s")
            pyautogui.click()
            time.sleep(0.6)
            universe.press("s", 0.5)
            pyautogui.click()
            time.sleep(0.5)
            universe.press("w", 1.6)
            pyautogui.click()
    else:
        # 黄泉模式:使用秘技
        keyops.keyUp("w")
        for iteration in range(2):
            universe.use_e()
            if iteration:
                time.sleep(0.6)
            universe.use_e()

            bw_map = universe.get_bw_map()
            if bw_map is None:
                continue

            universe.get_loc(bw_map, fbw=1, offset=universe.get_offset(2), rg=24)
            universe.get_real_loc(1)
            universe.press("w")
            universe.blessing()


def handle_target_type_3(universe, log) -> bool:
    """处理目标类型 3 的后续操作.

    目标类型 3 是传送点,需要多次尝试交互.

    Args:
        universe: UniverseUtils 实例
        log: 日志记录器

    Returns:
        True 如果成功处理,应该返回
    """
    for attempt in range(9):
        universe.get_screen()

        if universe.quan and universe.check("choose_blessing", 0.9266, 0.9491):
            return True

        if universe.check("f", 0.4443, 0.4417, mask="mask_f1", threshold=0.96):
            log.info("大图识别到传送点")
            universe.press("f")

            if universe.nof(must_be="tp"):
                time.sleep(1.5)
                return True

        universe.get_screen()

        if universe.isrun():
            if attempt in [0, 4]:
                universe.move_to_end()
            universe.press("w", 0.5)
            time.sleep(0.2)

    return False


def update_distance_history(
    distance_list: list,
    time_list: list,
    new_distance: float,
    sprint_used: int,
    slow_mode: bool,
) -> tuple:
    """更新距离历史记录.

    用于检测是否卡住(距离没有减少).

    Args:
        distance_list: 距离历史列表
        time_list: 时间历史列表
        new_distance: 新的距离值
        sprint_used: 是否使用冲刺
        slow_mode: 是否慢速模式

    Returns:
        (更新后的距离列表, 更新后的时间列表)
    """
    distance_list.append(new_distance)
    time_list.append(time.time())

    # 保留最近一段时间的记录
    window = 1.7 + sprint_used * 1 - slow_mode * 0.4

    while time_list[0] < time.time() - window:
        time_list = time_list[1:]
        distance_list = distance_list[1:]

    return distance_list, time_list
