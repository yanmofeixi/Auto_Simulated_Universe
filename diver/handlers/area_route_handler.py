"""差分宇宙区域寻路与交互处理器.

OCR匹配事件名逻辑:
1. 进入房间，移动到合适位置
2. 旋转视角用 OCR 匹配事件名，找到后旋转使其居中
3. 按 W 前进 + 按 F 进入事件处理
4. 处理完继续搜索第二个事件
5. 完成后旋转视角搜索传送门离开
"""

from __future__ import annotations

import json
import time
from typing import Optional, List, Tuple

import win32api
import win32con

import diver.keyops as keyops
from utils.common.ocr_utils import fuzzy_match
from utils.log import log


# 缓存事件名列表
_EVENT_NAMES_CACHE: Optional[List[str]] = None


def _load_event_names() -> List[str]:
    """加载事件名列表，使用缓存避免重复读取."""
    global _EVENT_NAMES_CACHE
    if _EVENT_NAMES_CACHE is None:
        try:
            with open("actions/event.json", "r", encoding="utf-8") as f:
                events = json.load(f)
            _EVENT_NAMES_CACHE = [e["name"] for e in events if e.get("name")]
            log.info(f"[OCR事件匹配] 加载了 {len(_EVENT_NAMES_CACHE)} 个事件名")
        except Exception as e:
            log.error(f"[OCR事件匹配] 加载事件名失败: {e}")
            _EVENT_NAMES_CACHE = []
    return _EVENT_NAMES_CACHE


# 模块加载时预加载事件名
_load_event_names()


def _fuzzy_match_event_name(ocr_text: str, event_names: List[str]) -> Optional[str]:
    """使用 fuzzy match 查找匹配的事件名，优先返回最长匹配."""
    if not ocr_text or len(ocr_text) < 2:
        return None
    
    matched = []
    for event_name in event_names:
        if len(event_name) >= 2 and fuzzy_match(event_name, ocr_text):
            matched.append(event_name)
    
    return max(matched, key=len) if matched else None


def _ocr_screen_for_event_names(universe) -> List[Tuple[str, int, int]]:
    """对屏幕进行 OCR，返回匹配的事件列表 [(事件名, x, y), ...]."""
    event_names = _load_event_names()
    if not event_names:
        return []
    
    universe.get_screen()
    universe.ts.forward(universe.screen)
    
    matched_events = []
    for res in universe.ts.res:
        raw_text = res.get("raw_text", "")
        box = res.get("box", [0, 0, 0, 0])
        
        if len(raw_text) < 2:
            continue
        
        matched_event = _fuzzy_match_event_name(raw_text, event_names)
        if matched_event:
            x_center = (box[0] + box[1]) // 2
            y_center = (box[2] + box[3]) // 2
            matched_events.append((matched_event, x_center, y_center))
            log.info(f"[OCR事件匹配] 识别到: '{matched_event}' (OCR: '{raw_text}') @ ({x_center}, {y_center})")
    
    return matched_events


def _rotate_and_search_event(universe, max_steps: int = 8) -> Optional[Tuple[str, int, int]]:
    """旋转视角搜索事件名，返回 (事件名, x, y) 或 None."""
    rotation_angles = [0, 45, 45, 45, 45, -90, -90, -90, -90]
    
    log.info("[OCR事件匹配] 开始旋转搜索事件名...")
    
    for i, angle in enumerate(rotation_angles[:max_steps + 1]):
        if angle != 0:
            universe.mouse_move(angle)
            time.sleep(0.3)
        
        matched = _ocr_screen_for_event_names(universe)
        if matched:
            event_name, x, y = matched[0]
            log.info(f"[OCR事件匹配] 第 {i} 次旋转找到: '{event_name}' @ ({x}, {y})")
            return (event_name, x, y)
    
    log.info("[OCR事件匹配] 旋转搜索完毕，未找到事件")
    return None


def _center_event_in_view(universe, event_x: int, screen_center: int = 960) -> None:
    """旋转视角使事件名居中."""
    offset = event_x - screen_center
    
    if abs(offset) < 50:
        log.info(f"[OCR事件匹配] 事件已居中 (偏移: {offset})")
        return
    
    rotation_angle = max(-30, min(30, offset * 0.08))
    log.info(f"[OCR事件匹配] 调整居中: 偏移={offset}, 旋转={rotation_angle:.1f}")
    universe.mouse_move(rotation_angle)
    time.sleep(0.2)


def _approach_and_interact_event(universe, max_time: float = 10.0) -> bool:
    """向事件前进并尝试交互，返回是否成功进入事件."""
    log.info("[OCR事件匹配] 向事件前进...")
    
    start_time = time.time()
    attempts = 0
    
    while time.time() - start_time < max_time:
        keyops.keyDown('w')
        time.sleep(0.5)
        keyops.keyUp('w')
        time.sleep(0.3)
        universe.get_screen()
        
        if universe.check_f(is_in=["事件", "奖励", "遭遇", "交易"]):
            log.info("[OCR事件匹配] 检测到交互，按 F")
            universe.press('f')
            time.sleep(0.8)
            
            universe.ts.forward(universe.get_screen())
            area_text = universe.clean_text(
                universe.ts.ocr_one_row(universe.screen, [50, 350, 3, 35]), char=0
            )
            
            if "事件" in area_text or "位面" not in area_text:
                log.info("[OCR事件匹配] 成功进入事件界面")
                return True
        
        if not universe.check("run", 0.876, 0.7815, threshold=0.91):
            universe.ts.forward(universe.get_screen())
            area_text = universe.clean_text(
                universe.ts.ocr_one_row(universe.screen, [92, 195, 54, 88]), char=0
            )
            if "事件" in area_text:
                log.info("[OCR事件匹配] 已进入事件界面")
                return True
        
        attempts += 1
    
    log.info(f"[OCR事件匹配] 接近超时，尝试 {attempts} 次")
    return False


def _handle_event_with_ocr(universe, event_number: int) -> bool:
    """使用 OCR 处理单个事件，返回是否成功."""
    log.info(f"[OCR事件匹配] === 搜索第 {event_number} 个事件 ===")
    
    event_info = _rotate_and_search_event(universe)
    if event_info is None:
        log.info(f"[OCR事件匹配] 未找到第 {event_number} 个事件")
        return False
    
    event_name, event_x, event_y = event_info
    log.info(f"[OCR事件匹配] 找到: '{event_name}' @ ({event_x}, {event_y})")
    
    _center_event_in_view(universe, event_x)
    
    if _approach_and_interact_event(universe):
        log.info(f"[OCR事件匹配] 第 {event_number} 个事件开始处理")
        
        while True:
            universe.ts.forward(universe.get_screen())
            area_text = universe.clean_text(
                universe.ts.ocr_one_row(universe.screen, [50, 350, 3, 35]), char=0
            )
            
            if "位面" in area_text or "区域" in area_text:
                log.info(f"[OCR事件匹配] 第 {event_number} 个事件处理完成")
                return True
            
            event_indicator = universe.merge_text(
                universe.ts.find_with_box([92, 195, 54, 88])
            )
            if "事件" in event_indicator:
                from diver.handlers.event_handler import handle_event
                handle_event(universe)
                time.sleep(0.5)
            else:
                universe.run_static()
                time.sleep(0.3)
    
    log.info(f"[OCR事件匹配] 无法接近第 {event_number} 个事件")
    return False


def _initial_movement(universe) -> bool:
    """初始移动到合适位置，返回是否成功."""
    log.info("[事件房处理] 初始移动...")
    
    keyops.keyDown('w')
    start_time = time.time()
    universe.get_screen()
    universe.get_text_position()
    
    while time.time() - start_time < 15:
        universe.get_screen()
        events = universe.get_text_position()
        if events:
            keyops.keyUp('w')
            # 稍微后退一点，避免走太近
            universe.press('s', 0.5)
            time.sleep(0.3)
            
            # 多次检测取最佳结果
            best_events = []
            for _ in range(3):
                universe.get_screen()
                detected = universe.get_text_position(1)
                if len(detected) > len(best_events):
                    best_events = detected
                if len(best_events) >= 2:
                    break
                time.sleep(0.2)
            
            if best_events and best_events[0][0] < 1600:
                log.info(f"[事件房处理] 初始移动完成，检测到位置: {best_events}")
                
                # 调整视角
                if not (933 <= best_events[0][0] <= 972):
                    win32api.mouse_event(
                        win32con.MOUSEEVENTF_MOVE, 0,
                        int(-100 * universe.multi * universe.scale)
                    )
                    time.sleep(0.3)
                
                return True
            else:
                keyops.keyDown('w')
                time.sleep(1)
                start_time += 1.5
    
    keyops.keyUp('w')
    log.error("[事件房处理] 初始移动超时")
    return False


def handle_event_reward_encounter(universe):
    """处理【事件/奖励/遭遇】区域.
    
    - state=0: 初始移动 + OCR搜索处理第一个事件
    - state=1: OCR搜索处理第二个事件
    - state=2: 寻找传送门离开
    
    返回: 1=结束探索, None=继续
    """
    log.info(f"[事件房处理] area_state={universe.area_state}")

    if universe.da_hei_ta and universe.allow_e and not universe.da_hei_ta_effecting:
        universe.skill()
        universe.da_hei_ta_effecting = True

    if universe.area_state == 0:
        log.info("[事件房处理] === State 0: 初始移动 + OCR搜索事件 ===")
        
        if not _initial_movement(universe):
            universe.close_and_exit()
            return 1
        
        # 检查是否已有传送门
        portal = universe.find_portal()
        if portal['nums'] > 0:
            log.info("[事件房处理] 已有传送门，跳过事件处理")
            universe.area_state = 2
            return None
        
        # OCR 搜索并处理第一个事件
        if _handle_event_with_ocr(universe, 1):
            log.info("[事件房处理] 第一个事件完成，进入 state=1")
            universe.area_state = 1
        else:
            log.info("[事件房处理] 未找到事件，进入 state=2")
            universe.area_state = 2

    elif universe.area_state == 1:
        log.info("[事件房处理] === State 1: OCR搜索第二个事件 ===")
        time.sleep(0.5)
        
        if _handle_event_with_ocr(universe, 2):
            log.info("[事件房处理] 第二个事件完成")
        else:
            log.info("[事件房处理] 未找到第二个事件")
        
        universe.area_state = 2
        log.info("[事件房处理] 进入 state=2 搜索传送门")

    else:
        log.info("[事件房处理] === State 2: 寻找传送门 ===")
        universe.portal_opening_days(static=1)

    return None
