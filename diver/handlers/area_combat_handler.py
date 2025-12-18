"""差分宇宙战斗相关区域(战斗/首领)处理器."""

from __future__ import annotations

import time

import pyautogui

import diver.keyops as keyops
from diver.config import config


def handle_battle_area(universe) -> None:
    """处理【战斗】区域."""

    # 如果大黑塔秘技使能,先使用秘技,前面应该已经切换到了大黑塔
    if universe.da_hei_ta and universe.allow_e and not universe.da_hei_ta_effecting:
        universe.skill()
        universe.da_hei_ta_effecting = True

    if universe.area_state == 0:
        keyops.keyDown('w')
        time.sleep(0.2)
        keyops.keyDown('shift')

        start_time = time.time()
        while time.time() - start_time < (1.45 if universe.bai_e else 3):
            universe.get_screen()
            if universe.check("divergent/z", 0.5771, 0.9546, mask="mask_z", threshold=0.96):
                break

        if not universe.bai_e:
            time.sleep(0.8)

        keyops.keyUp('w')
        keyops.keyUp('shift')

        if universe.quan and universe.allow_e:
            for _ in range(4):
                universe.skill(1)
            universe.press('w')
            time.sleep(1.5)
        elif universe.bai_e and universe.allow_e:
            for _ in range(4):
                universe.skill(1)
            time.sleep(1.5)
        else:
            pyautogui.click()

        universe.area_state += 1
    else:
        if not ((universe.quan or universe.bai_e) and universe.allow_e):
            universe.press('w', 0.25)
        universe.portal_opening_days(static=1)


def handle_boss_area(universe) -> int | None:
    """处理【首领】区域.

    返回值:
    - `1`:本次探索结束.
    - `None`:继续流程.
    """

    if universe.floor == 13 and universe.area_state > 0:
        # 已经结束战斗了,增加计数并通知
        if not universe.boss_counted:
            universe.boss_counted = True
            universe.add_count_and_notify()
        universe.close_and_exit()
        universe.end_of_uni()
        return 1

    if universe.area_state == 0:
        universe.boss_counted = False  # 进入新的首领房,重置标志位
        universe.press('w', 3)

        for character_name in config.skill_char:
            # 使用子字符串匹配检查角色是否在队伍中
            in_team = universe.has_team_member(character_name) if not character_name.isdigit() else True
            if not (in_team and universe.allow_e):
                continue

            if character_name == '大黑塔' and universe.da_hei_ta_effecting:
                # 大黑塔秘技生效中,跳过
                continue

            if character_name.isdigit():
                key = int(character_name)
            else:
                pos = universe.get_team_member_position(character_name)
                key = pos + 1 if pos is not None else None

            if key is None:
                continue

            universe.press(str(key))
            time.sleep(0.8)
            universe.check_dead()
            universe.skill()
            time.sleep(1.5)

        pyautogui.click()
        time.sleep(0.2)
        pyautogui.click()
        universe.area_state += 1
    else:
        # 战斗结束了,增加计数并通知
        if not universe.boss_counted:
            universe.boss_counted = True
            universe.add_count_and_notify()
        time.sleep(1)
        universe.portal_opening_days(static=1)

    return None
