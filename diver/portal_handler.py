"""传送门处理模块.

该模块负责:
- 传送门检测和瞄准
- 传送门导航
- 区域切换处理
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass


def search_portal_with_rotation(universe, angles: list) -> tuple:
    """通过旋转视角搜索传送门.

    依次尝试不同角度,直到找到传送门.

    Args:
        universe: DivergentUniverse 实例
        angles: 要尝试的角度列表

    Returns:
        (传送门信息, 找到传送门时的角度索引)
    """
    for index, angle in enumerate(angles):
        universe.mouse_move(angle)
        time.sleep(0.2)
        portal = universe.find_portal()

        if portal["score"]:
            return portal, index

    return {"score": 0, "nums": 0, "type": ""}, len(angles)


def search_alternative_portal(
    universe,
    current_portal: dict,
    angles: list,
    start_index: int,
) -> dict:
    """搜索替代传送门.

    当当前传送门评分较低时,尝试找到更好的选择.

    Args:
        universe: DivergentUniverse 实例
        current_portal: 当前找到的传送门
        angles: 角度列表
        start_index: 开始搜索的角度索引

    Returns:
        最佳传送门信息
    """
    portal_type = current_portal["type"]
    bias = 0

    for i in range(start_index + 1, len(angles)):
        universe.mouse_move(angles[i])
        bias += angles[i]
        time.sleep(0.2)

        portal_after = universe.find_portal()

        if portal_after["score"] and portal_type != portal_after["type"]:
            return portal_after

    # 没找到更好的,恢复视角并返回原传送门
    if current_portal["type"] == portal_type:
        universe.mouse_move(-bias)
        return current_portal

    return current_portal


def aim_at_portal(universe, portal: dict, config) -> dict | None:
    """瞄准传送门.

    调整视角使传送门居中.

    Args:
        universe: DivergentUniverse 实例
        portal: 传送门信息
        config: 配置对象

    Returns:
        更新后的传送门信息,或 None 如果丢失目标
    """
    import bisect

    zero = bisect.bisect_left(config.angles, 0)

    while abs(universe.portal_bias(portal)) > 50:
        angle = bisect.bisect_left(config.angles, universe.portal_bias(portal)) - zero
        universe.mouse_move(angle)

        if abs(universe.portal_bias(portal)) < 200:
            return portal

        time.sleep(0.2)
        portal_after = universe.find_portal(portal["type"])

        if portal_after["score"] == 0:
            universe.press("w", 1)
            portal_after = universe.find_portal(portal["type"])

            if portal_after["score"] == 0:
                return None

        portal = portal_after

    return portal


def move_toward_portal(universe, portal: dict, keyops, moving: bool) -> tuple:
    """向传送门移动.

    Args:
        universe: DivergentUniverse 实例
        portal: 传送门信息
        keyops: 按键操作模块
        moving: 是否正在移动

    Returns:
        (是否找到入口, 是否正在移动)
    """
    text_list = [portal["type"]] if portal["score"] else ["区域", "结束", "退出"]

    if universe.forward_until(text_list, timeout=2.5, moving=moving):
        universe.init_floor()
        return True, moving

    return False, moving


def handle_portal_not_found(universe, keyops) -> None:
    """处理未找到传送门的情况.

    停止移动并调整位置.

    Args:
        universe: DivergentUniverse 实例
        keyops: 按键操作模块
    """
    keyops.keyUp("w")
    universe.press("d", 0.6)


def portal_navigation_loop(
    universe,
    portal: dict,
    keyops,
    config,
    aimed: bool = False,
) -> tuple:
    """传送门导航主循环.

    持续调整方向并向传送门移动.

    Args:
        universe: DivergentUniverse 实例
        portal: 初始传送门信息
        keyops: 按键操作模块
        config: 配置对象
        aimed: 是否已瞄准

    Returns:
        (是否成功, 更新后的瞄准状态)
    """
    moving = False
    start_time = time.time()
    timeout = 5 + 2 * (portal["score"] != 0)

    while time.time() - start_time < timeout:
        # 如果未瞄准,先搜索传送门
        if not aimed:
            if portal["score"] == 0:
                portal = universe.find_portal()
        else:
            # 已瞄准,尝试前进
            found, moving = move_toward_portal(universe, portal, keyops, moving)

            if found:
                return True, aimed

            # 没找到,调整位置重试
            handle_portal_not_found(universe, keyops)
            moving = False
            return False, aimed  # 需要重试

        # 找到传送门后进行瞄准
        if portal["score"] and not aimed:
            if moving:
                print("stop moving")
                keyops.keyUp("w")
                moving = False
                universe.press("s", min(max(universe.ocr_time_list), 0.4))
                continue
            else:
                print("aiming...")
                tmp_portal = aim_at_portal(universe, portal, config)

                if tmp_portal is None:
                    return False, aimed  # 需要重试

                portal = tmp_portal
                aimed = True
                moving = True
                keyops.keyDown("w")

        elif portal["score"] == 0:
            # 没找到传送门,继续前进搜索
            if not moving:
                keyops.keyDown("w")
                moving = True

    if moving:
        keyops.keyUp("w")

    return True, aimed


def execute_portal_navigation(
    universe,
    keyops,
    config,
    aimed: bool = False,
    static: bool = False,
    depth: int = 0,
) -> None:
    """执行传送门导航的主函数.

    整合所有子函数,实现完整的传送门导航流程.

    Args:
        universe: DivergentUniverse 实例
        keyops: 按键操作模块
        config: 配置对象
        aimed: 是否已瞄准
        static: 是否从静止状态开始搜索
        depth: 递归深度
    """
    # 递归深度检查
    if depth > 1:
        universe.close_and_exit(click=universe.fail_count > 1)
        universe.fail_count += 1
        return

    if depth == 0:
        universe.portal_cnt += 1

    portal = {"score": 0, "nums": 0, "type": ""}

    # 静止状态下的搜索
    if static:
        angles = [0, 90, 90, 90, 45, -90, -90, -90, -45]
        portal, found_index = search_portal_with_rotation(universe, angles)

        # 检查是否需要寻找替代传送门
        special_floors = [1, 2, 4, 5, 6, 7, 9, 10]
        if universe.floor in special_floors:
            if portal["nums"] == 1 and portal["score"] < 2:
                portal = search_alternative_portal(
                    universe, portal, angles, found_index
                )

    # 执行导航循环
    success, aimed = portal_navigation_loop(
        universe, portal, keyops, config, aimed
    )

    if not success:
        # 导航失败,递归重试
        execute_portal_navigation(
            universe, keyops, config,
            aimed=False, static=True, depth=depth + 1
        )
