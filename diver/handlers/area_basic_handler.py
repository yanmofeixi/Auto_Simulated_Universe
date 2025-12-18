"""差分宇宙基础区域(休整/商店/财富/位面)处理器."""

from __future__ import annotations

import time

import pyautogui

import diver.keyops as keyops


def handle_rest_area(universe) -> None:
    """处理【休整】区域."""

    pyautogui.click()
    universe.check_pop(timeout_s=3.0, poll_interval_s=0.5, after_action_sleep_s=0.3)
    time.sleep(0.3)
    keyops.keyDown('w')
    universe.press('a', 0.45)
    time.sleep(1.5)
    keyops.keyUp('w')
    time.sleep(0.25)
    universe.portal_opening_days(static=1)


def handle_shop_area(universe) -> None:
    """处理【商店】区域."""

    pyautogui.click()
    universe.check_pop(timeout_s=3.0, poll_interval_s=0.5, after_action_sleep_s=0.3)
    time.sleep(0.3)
    keyops.keyDown('w')
    time.sleep(1.8)
    # universe.press('d', 0.4)
    keyops.keyUp('w')
    time.sleep(0.6)
    universe.portal_opening_days(static=1)


def handle_wealth_area(universe) -> None:
    """处理【财富】区域."""

    keyops.keyDown('w')
    time.sleep(1.6)
    universe.press('a', 0.5)
    keyops.keyUp('w')

    pyautogui.click()
    # 财富区交互/弹窗出现相对更慢,适当延长 timeout.
    universe.check_pop(timeout_s=6.0, poll_interval_s=0.5, after_action_sleep_s=0.3)
    time.sleep(0.7)

    result = universe.forward_until(text_list=['战利品', '药箱'], timeout=3.0, moving=0)
    if not result:
        pyautogui.click()
        universe.check_pop(timeout_s=6.0, poll_interval_s=0.5, after_action_sleep_s=0.3)
        time.sleep(0.7)
        universe.forward_until(text_list=['战利品', '药箱'], timeout=1.0, moving=0)

    time.sleep(1.4)
    universe.portal_opening_days(static=1)


def handle_plane_area(universe) -> None:
    """处理【位面】区域."""

    pyautogui.click()
    time.sleep(2)
    universe.close_and_exit()
