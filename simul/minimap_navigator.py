"""基于小地图的实时探索寻路模块.

当预录制地图匹配失败时,使用此模块作为后备寻路方案.
核心思路:
1. 实时拼接小地图构建探索地图
2. 在小地图上检测交互图标(门/怪物/红点)
3. 无可见目标时,向未探索的前沿区域移动
4. 检测卡住并自动恢复
"""

import math
import random
import time

import cv2 as cv
import numpy as np

from simul.keyops import keyDown, keyUp
from utils.log import log


# 探索地图大小 (与 init_map 中 big_map 一致)
MAP_SIZE = 8192
MAP_CENTER = 4096

# 小地图参数
MINIMAP_RADIUS = 82
MINIMAP_CENTER = (88, 88)  # bw_map 中心
ARROW_CENTER = (120, 128)  # local_screen 中 player 大致位置

# 图标匹配阈值
ICON_THRESHOLD = 0.85
RED_COLOR_THRESHOLD = 512

# 前沿搜索参数
FRONTIER_GRID = 4
FRONTIER_MIN_DIST = 15
FRONTIER_MAX_DIST = 200

# 卡住检测
STUCK_TIME = 4.0
STUCK_DIST = 5


class MinimapNavigator:
    """基于小地图的实时探索导航器.

    在不依赖预录制地图数据的情况下,通过持续读取小地图来:
    - 构建实时探索地图
    - 检测并导航到可见目标 (交互图标/敌人/传送门)
    - 进行前沿探索以发现新区域
    """

    def __init__(self, utils):
        """初始化导航器.

        Args:
            utils: SimulatedUniverse 实例,提供截图/按键/小地图等基础能力
        """
        self.u = utils
        # 直接使用 utils.big_map 作为探索地图 (由 init_map 初始化为 8192x8192)
        # visited_cells: 记录已访问过的前沿区域 (量化到网格)
        self.visited_cells = {}  # {(gi, gj): visit_count}
        self.pos = (MAP_CENTER, MAP_CENTER)
        self.heading = 0
        self.last_pos = (MAP_CENTER, MAP_CENTER)
        self.last_move_time = time.time()
        self.stuck_recovery_count = 0
        self.total_steps = 0
        self.turn_history = []  # 最近的转向记录,用于避免重复绕圈

    def navigate(self):
        """主导航循环 — 替代 get_direc(),持续探索直到找到出口.

        返回后,调用者应检查是否触发了 F 交互或进入了战斗.
        """
        log.info("[探索] ====== 开始基于小地图的实时探索 ======")
        log.info(f"[探索] big_map shape={self.u.big_map.shape}, floor={self.u.floor}")

        # 使用已有的 big_map (init_map 初始化为全零 8192x8192)
        self.u.now_loc = (MAP_CENTER, MAP_CENTER)
        self.pos = (MAP_CENTER, MAP_CENTER)
        log.info(f"[探索] 初始位置=({MAP_CENTER},{MAP_CENTER})")

        # 先静止拍一张小地图,确定初始方位
        bw_map = self.u.get_bw_map(gs=0)
        if bw_map is not None:
            white_px = int(np.count_nonzero(bw_map == 255))
            log.info(f"[探索] 初始小地图: shape={bw_map.shape}, 白色像素={white_px}")
            self._stitch_map(bw_map)
        else:
            log.warning("[探索] 初始小地图获取失败 (bw_map=None)")

        shape = (int(self.u.scx * 190), int(self.u.scx * 190))
        local_screen = self.u.get_local(0.9333, 0.8657, shape)
        raw_direc = self.u.get_now_direc(local_screen)
        self.heading = 360 - raw_direc - 90
        log.info(f"[探索] 初始朝向: raw_direc={raw_direc}, heading={self.heading:.1f}")

        keyDown("w")
        self.u.sprint()
        self.last_move_time = time.time()

        try:
            while not self.u._stop:
                self.total_steps += 1
                step_start = time.time()

                # 每10步输出一次状态摘要
                if self.total_steps % 10 == 1:
                    explored = int(np.count_nonzero(self.u.big_map >= 100))
                    scanned = int(np.count_nonzero(self.u.big_map > 0))
                    log.info(
                        f"[探索] --- step={self.total_steps} pos={self.pos} "
                        f"heading={self.heading:.0f} explored_px={explored} "
                        f"scanned_px={scanned} visited_cells={len(self.visited_cells)} "
                        f"stuck_cnt={self.stuck_recovery_count} ---"
                    )

                # 1. 检查是否进入了非跑图状态
                self.u.get_screen()
                if not self.u.isrun():
                    log.info("[探索] 不再处于跑图状态 (isrun=False),退出探索")
                    break

                # 2. 检查 F 交互
                if self.u.goodf() and not self.u.ts.sim("黑塔"):
                    log.info(f"[探索] 发现可交互点! text='{self.u.ts.text}' pos={self.pos}")
                    break

                # 2.5 检查战斗状态 (遇到了怪物)
                if self.u.check("auto_2", 0.0583, 0.0769) or self.u.check(
                    "c", 0.9464, 0.1287, threshold=0.985
                ):
                    log.info(f"[探索] 进入战斗! pos={self.pos} step={self.total_steps}")
                    break

                # 3. 获取小地图数据
                bw_map = self.u.get_bw_map()
                if bw_map is None:
                    log.debug("[探索] bw_map=None (可能在选祝福),等待...")
                    time.sleep(0.3)
                    continue

                # 4. 定位
                old_pos = self.pos
                self.u.get_loc(bw_map, rg=30)
                self.pos = self.u.now_loc
                move_dist = self.u.get_dis(old_pos, self.pos)
                self._stitch_map(bw_map)

                # 5. 获取当前朝向
                self.u.get_screen()
                local_screen = self.u.get_local(0.9333, 0.8657, shape)
                raw_direc = self.u.get_now_direc(local_screen)
                self.heading = 360 - raw_direc - 90

                if self.total_steps % 5 == 0:
                    log.info(
                        f"[探索] 位置更新: {old_pos}->{self.pos} "
                        f"移动={move_dist:.1f} heading={self.heading:.0f}"
                    )

                # 6. 在小地图上寻找图标目标
                icon_angle = self._detect_minimap_icons(local_screen)
                if icon_angle is not None:
                    log.info(f"[探索] 图标导航: 转向 {icon_angle:.1f}°")
                    self._turn_toward(icon_angle)
                    # 发现目标时刷新超时计时器
                    self.u.lst_changed = time.time()
                    time.sleep(0.3)
                    continue

                # 7. 卡住检测
                if self._is_stuck():
                    self._recover_from_stuck()
                    continue

                # 8. 前沿探索
                frontier = self._find_best_frontier()
                if frontier is not None:
                    target_angle = self._angle_to(frontier)
                    fdist = self.u.get_dis(self.pos, frontier)
                    if self.total_steps % 5 == 0:
                        log.info(
                            f"[探索] 前沿导航: target={frontier} "
                            f"dist={fdist:.0f} angle={target_angle:.1f}°"
                        )
                    self._turn_toward(target_angle)
                else:
                    # 没有前沿 = 可能已经探索完了,尝试向未走过的方向转
                    log.info("[探索] 无可用前沿,随机探索")
                    self._explore_random()

                # 定期刷新超时计时器 (只要还在移动就不算卡死)
                if not self._is_stuck():
                    self.u.lst_changed = time.time()

                step_elapsed = time.time() - step_start
                if step_elapsed > 1.0:
                    log.warning(f"[探索] step={self.total_steps} 耗时过长: {step_elapsed:.2f}s")

                time.sleep(0.15)

        finally:
            keyUp("w")

        explored = int(np.count_nonzero(self.u.big_map >= 100))
        log.info(
            f"[探索] ====== 探索结束 ======\n"
            f"  总步数: {self.total_steps}\n"
            f"  最终位置: {self.pos}\n"
            f"  已探索像素: {explored}\n"
            f"  visited_cells: {len(self.visited_cells)}\n"
            f"  卡住恢复次数: {self.stuck_recovery_count}"
        )

    def _stitch_map(self, bw_map):
        """将当前小地图拼接到探索大地图中."""
        cx, cy = self.pos
        big_map = self.u.big_map
        new_white = 0
        new_scanned = 0
        for i in range(bw_map.shape[0]):
            for j in range(bw_map.shape[1]):
                if ((i - MINIMAP_CENTER[0]) ** 2 + (j - MINIMAP_CENTER[1]) ** 2) > MINIMAP_RADIUS ** 2:
                    continue
                ei = cx - MINIMAP_CENTER[0] + i
                ej = cy - MINIMAP_CENTER[1] + j
                if 0 <= ei < MAP_SIZE and 0 <= ej < MAP_SIZE:
                    if bw_map[i, j] == 255:
                        if big_map[ei, ej] < 50:  # 计算新发现的白色像素
                            new_white += 1
                        if big_map[ei, ej] < 250:
                            big_map[ei, ej] = min(big_map[ei, ej] + 50, 255)
                    elif big_map[ei, ej] == 0:
                        big_map[ei, ej] = 1
                        new_scanned += 1
        if new_white > 20 and self.total_steps % 3 == 0:
            log.info(f"[探索] 拼图: 新路径={new_white}px 新扫描={new_scanned}px")

    def _detect_minimap_icons(self, local_screen):
        """在小地图上检测交互图标.

        检测顺序: 门图标 > 黑塔图标 > 红色敌人
        返回目标相对于当前朝向的角度偏差, 或 None.
        """
        center = ARROW_CENTER

        # 裁剪到圆形区域内
        masked = local_screen.copy()
        for i in range(masked.shape[0]):
            for j in range(masked.shape[1]):
                if self.u.get_dis((i, j), center) >= MINIMAP_RADIUS:
                    masked[i, j] = [0, 0, 0]

        # 检测门/交互图标 (mini1, mini2, mini3)
        best_icon = None
        best_icon_val = 0
        for template_name in ["mini1", "mini2", "mini3"]:
            try:
                template = cv.imread(self.u.format_path(template_name))
                if template is None:
                    log.warning(f"[探索] 图标模板 {template_name} 加载失败")
                    continue
                result = cv.matchTemplate(masked, template, cv.TM_CCORR_NORMED)
                _, max_val, _, max_loc = cv.minMaxLoc(result)
                if self.total_steps % 10 == 1:
                    log.info(f"[探索] 图标检测 {template_name}: sim={max_val:.3f} threshold={ICON_THRESHOLD}")
                if max_val > ICON_THRESHOLD and max_val > best_icon_val:
                    sp = template.shape
                    target = (max_loc[1] + sp[0] // 2, max_loc[0] + sp[1] // 2)
                    dist = self.u.get_dis(target, center)
                    if dist > 5:
                        best_icon = (template_name, max_val, target, dist)
                        best_icon_val = max_val
            except Exception as e:
                log.warning(f"[探索] 图标检测异常 {template_name}: {e}")
                continue

        if best_icon is not None:
            template_name, max_val, target, dist = best_icon
            world_angle = math.atan2(
                target[0] - center[0], target[1] - center[1]
            ) / math.pi * 180
            angle_diff = world_angle - self.heading
            log.info(
                f"[探索] >>> 检测到图标 {template_name} <<<\n"
                f"  相似度={max_val:.3f} 位置=({target[0]:.0f},{target[1]:.0f}) "
                f"距离={dist:.1f} world_angle={world_angle:.1f} diff={angle_diff:.1f}"
            )
            return angle_diff

        # 检测红色敌人 (BGR: ~[60, 60, 226])
        red = np.array([60, 60, 226])
        red_mask = np.sum((masked.astype(np.int16) - red) ** 2, axis=-1) <= RED_COLOR_THRESHOLD
        red_points = np.where(red_mask)
        red_count = red_points[0].shape[0]
        if self.total_steps % 10 == 1:
            log.info(f"[探索] 红色像素检测: count={red_count} threshold=10")
        if red_count > 10:
            target = (float(np.mean(red_points[0])), float(np.mean(red_points[1])))
            dist = self.u.get_dis(target, center)
            if dist > 8:
                world_angle = math.atan2(
                    target[0] - center[0], target[1] - center[1]
                ) / math.pi * 180
                angle_diff = world_angle - self.heading
                log.info(
                    f"[探索] >>> 检测到红色敌人 <<<\n"
                    f"  像素数={red_count} 中心=({target[0]:.0f},{target[1]:.0f}) "
                    f"距离={dist:.1f} angle_diff={angle_diff:.1f}"
                )
                return angle_diff

        return None

    def _find_best_frontier(self):
        """在探索地图上寻找最佳前沿点.

        前沿 = 已知路径 (白色, >=100) 旁边的未扫描区域 (==0).
        在所有前沿中,选择距离适中且方向偏好的那个.
        """
        cx, cy = self.pos
        big_map = self.u.big_map
        best = None
        best_score = -1
        candidates = 0

        # 在一定范围内搜索
        search_radius = 150
        step = FRONTIER_GRID

        for di in range(-search_radius, search_radius + 1, step):
            for dj in range(-search_radius, search_radius + 1, step):
                ei, ej = cx + di, cy + dj
                if not (0 <= ei < MAP_SIZE and 0 <= ej < MAP_SIZE):
                    continue

                dist = math.sqrt(di * di + dj * dj)
                if dist < FRONTIER_MIN_DIST or dist > FRONTIER_MAX_DIST:
                    continue

                # 该点必须是未扫描的 (==0)
                if big_map[ei, ej] != 0:
                    continue

                # 检查邻近是否有已知路径 (>=100)
                has_path_neighbor = False
                for ni, nj in [(-step, 0), (step, 0), (0, -step), (0, step)]:
                    ni2, nj2 = ei + ni, ej + nj
                    if 0 <= ni2 < MAP_SIZE and 0 <= nj2 < MAP_SIZE:
                        if big_map[ni2, nj2] >= 100:
                            has_path_neighbor = True
                            break

                if not has_path_neighbor:
                    continue

                candidates += 1

                # 已经作为前沿访问过的区域降低优先级
                grid_key = (ei // 16, ej // 16)
                visited_count = self.visited_cells.get(grid_key, 0)
                visited_penalty = visited_count * 20

                # 评分: 近的更好, 但太近的不好; 未去过的更好
                score = 1000.0 / (dist + 10) - visited_penalty

                if score > best_score:
                    best_score = score
                    best = (ei, ej)

        if best is not None:
            grid_key = (best[0] // 16, best[1] // 16)
            visit_cnt = self.visited_cells.get(grid_key, 0)
            self.visited_cells[grid_key] = visit_cnt + 1
            if self.total_steps % 5 == 0:
                log.info(
                    f"[探索] 前沿搜索: candidates={candidates} best={best} "
                    f"score={best_score:.1f} visit_cnt={visit_cnt}"
                )
        else:
            log.info(f"[探索] 前沿搜索: candidates={candidates} 无可用前沿")

        return best

    def _angle_to(self, target):
        """计算从当前位置到目标点的角度偏差（相对于当前朝向）."""
        cx, cy = self.pos
        dx = target[0] - cx
        dy = target[1] - cy
        world_angle = math.atan2(dx, dy) / math.pi * 180
        sub = world_angle - self.heading
        while sub < -180:
            sub += 360
        while sub > 180:
            sub -= 360
        return sub

    def _turn_toward(self, angle_diff):
        """转向指定的角度偏差."""
        # 限幅防止过度转向
        while angle_diff < -180:
            angle_diff += 360
        while angle_diff > 180:
            angle_diff -= 360

        self.u.mouse_move(angle_diff)
        self.heading += angle_diff
        self.last_move_time = time.time()
        self.last_pos = self.pos

    def _is_stuck(self):
        """检测是否卡住 (长时间位置未变化)."""
        dist = self.u.get_dis(self.pos, self.last_pos)
        elapsed = time.time() - self.last_move_time

        if dist > STUCK_DIST:
            self.last_pos = self.pos
            self.last_move_time = time.time()
            self.stuck_recovery_count = 0
            return False

        return elapsed > STUCK_TIME

    def _recover_from_stuck(self):
        """从卡住状态恢复."""
        self.stuck_recovery_count += 1
        elapsed = time.time() - self.last_move_time
        dist = self.u.get_dis(self.pos, self.last_pos)
        log.info(
            f"[探索] !!! 卡住恢复 #{self.stuck_recovery_count} !!!\n"
            f"  pos={self.pos} last_pos={self.last_pos} dist={dist:.1f}\n"
            f"  since_last_move={elapsed:.1f}s heading={self.heading:.0f}"
        )

        keyUp("w")

        if self.stuck_recovery_count <= 2:
            # 后退 + 侧移 + 前进
            dirs = ["s", "a", "d"]
            random.shuffle(dirs)
            self.u.press("s", 0.4)
            self.u.press(dirs[0], 0.3 + random.random() * 0.4)
            # 转一个随机角度
            angle = random.choice([-90, -60, 60, 90, 120, -120])
            self.u.mouse_move(angle)
            self.heading += angle
        elif self.stuck_recovery_count <= 4:
            # 更大范围的转向 + 移动
            self.u.press("s", 0.5)
            angle = random.choice([-150, -120, 120, 150, 180])
            self.u.mouse_move(angle)
            self.heading += angle
            self.u.press("w", 0.6)
            self.u.press(random.choice(["a", "d"]), 0.5)
        else:
            # 极端情况: 大幅转向尝试找到新路
            self.u.press("s", 0.6)
            for d in ["a", "w", "d", "w", "a", "w"]:
                self.u.press(d, 0.3)
            self.stuck_recovery_count = 0

        if not self.u._stop:
            keyDown("w")
            self.u.sprint()

        self.last_pos = self.pos
        self.last_move_time = time.time()

    def _explore_random(self):
        """无前沿可用时,随机换方向探索."""
        angle = random.choice([-45, -30, 30, 45, -60, 60])
        log.info(f"[探索] 随机探索: 转向 {angle}°  (heading {self.heading:.0f} -> {self.heading + angle:.0f})")
        self.u.mouse_move(angle)
        self.heading += angle
        time.sleep(0.2)
