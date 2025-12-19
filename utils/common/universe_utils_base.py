"""UniverseUtils 基类模块.

该模块提供 simul 和 diver 共用的基类,包含:
- 屏幕截图和图像处理
- 键鼠输入控制
- 小地图导航和寻路
- 模板匹配

子类 (simul/utils.py 和 diver/utils.py) 继承此基类,
只需实现各自特有的逻辑.
"""

from __future__ import annotations

import math
import sys
import time
import traceback
from copy import deepcopy
from math import cos, sin
from typing import TYPE_CHECKING, Callable, Optional, Tuple

import cv2 as cv
import numpy as np
import pyautogui
import win32api
import win32con

from utils.common.config_base import is_game_window
from utils.common.constants import (
    Colors,
    ColorThresholds,
    HSVRanges,
    MatchThresholds,
    MinimapCoords,
    MorphologyKernels,
    MouseParams,
    TargetDistances,
    UICoords,
)
from utils.common.image_processing import (
    apply_circular_mask,
    check_auto_battle,
    check_running_state,
    create_color_mask,
    crop_minimap,
    create_end_point_map,
    dilate,
    euclidean_distance,
    extract_orb_features,
    match_features,
    rotate_image,
)
from utils.common.minimap_ops import (
    exist_minimap as common_exist_minimap,
    get_now_direc as common_get_now_direc,
    take_fine_minimap as common_take_fine_minimap,
)
from utils.common.screen_ops import get_local as common_get_local
from utils.common.template_match import match_template_near_point
from utils.common.ui_ops import (
    calc_point as common_calc_point,
    click as common_click,
    click_box as common_click_box,
    click_position as common_click_position,
    debug_print_point as common_debug_print_point,
    drag as common_drag,
    gen_hotkey_img as common_gen_hotkey_img,
    press_key as common_press_key,
    sprint as common_sprint,
    wait_fig as common_wait_fig,
)
from utils.common.vision import (
    calculated as common_calculated,
    click_target as common_click_target,
    scan_screenshot as common_scan_screenshot,
)
from utils.common.window_manager import (
    set_game_foreground,
    wait_for_game_window_context,
)
from utils.screenshot import Screen

if TYPE_CHECKING:
    from numpy import ndarray


class UniverseUtilsBase:
    """模拟宇宙/差分宇宙工具基类.

    该类提供两个模式共用的基础功能:
    - 屏幕截图和图像处理
    - 键鼠输入控制
    - 小地图导航和寻路
    - 模板匹配和 OCR 识别
    - 游戏窗口管理

    子类需要:
    1. 提供 config, keyops, ocr, log 等模块引用
    2. 实现 format_path() 返回正确的图片路径格式
    3. 根据需要覆盖特定方法
    """

    # ===== 子类需要提供的属性 =====
    # 这些属性应在子类的 __init__ 中设置

    # 配置模块
    config = None
    # 按键操作模块
    keyops = None
    # OCR 模块
    ocr = None
    # 日志模块
    log = None

    # ===== 默认阈值 =====
    threshold: float = MatchThresholds.DEFAULT

    def __init__(self):
        """初始化基类.

        注意: 子类应在调用此方法前设置 config, keyops, ocr, log 属性.
        """
        # 基础标志位
        self.check_bonus = 1
        self._stop = False
        self.stop_move = 0
        self.move = 0
        self.fail_count = 0
        self.first_mini = 1
        self.last_info = ""
        self.mini_target = 0
        self.f_time = 0
        self.init_ang = 0
        self.allow_e = 1
        self.quan = 0
        self.img_map = dict()
        self.find = 1

        # 基准分辨率
        self.bx, self.by = 1920, 1080

        # 等待游戏窗口
        if self.log:
            self.log.warning("等待游戏窗口")

        ctx = wait_for_game_window_context(log=self.log)
        self.x0, self.y0, self.x1, self.y1 = ctx.x0, ctx.y0, ctx.x1, ctx.y1
        self.xx, self.yy = ctx.width, ctx.height
        self.full = ctx.is_fullscreen
        self.scx, self.scy = ctx.scx, ctx.scy
        self.scale = ctx.dpi_scale
        self.real_width = ctx.real_width

        # 配置相关属性
        if self.config:
            self.multi = getattr(self.config, "multi", 1.0)
            self.diffi = getattr(self.config, "diffi", 1)
        else:
            self.multi = 1.0
            self.diffi = 1

        # 检查分辨率
        if self.xx != 1920 or self.yy != 1080:
            if self.log:
                self.log.error(f"分辨率错误 {self.xx} {self.yy} 请设为1920*1080")

        # 初始化截图工具
        self.sct = Screen()
        self.screen = None

    # ===== 路径格式化 (子类可覆盖) =====

    def format_path(self, path: str) -> str:
        """格式化图片路径.

        Args:
            path: 图片名称 (不含扩展名和前缀)

        Returns:
            完整的图片路径
        """
        return f"imgs/{path}.jpg"

    # ===== 热键图片生成 =====

    def gen_hotkey_img(self, hotkey: str = "e", bg: str = "imgs/f_bg.jpg"):
        """生成热键提示图片."""
        return common_gen_hotkey_img(hotkey=hotkey, bg=bg)

    # ===== 按键操作 =====

    def press(self, c: str, t: float = 0):
        """按下并释放按键.

        Args:
            c: 按键名称
            t: 按住时长 (秒)
        """
        return common_press_key(
            key=c,
            duration=t,
            log=self.log,
            keyops=self.keyops,
            allow_e=bool(self.allow_e),
            stop_flag=lambda: self._stop,
        )

    def sprint(self):
        """冲刺 (按 shift)."""
        return common_sprint(
            log=self.log,
            keyops=self.keyops,
            press=lambda key, duration=0: self.press(key, duration),
        )

    # ===== 等待函数 =====

    def wait_fig(self, f: Callable[[], bool], timeout: float = 3) -> int:
        """等待条件变为 False.

        Args:
            f: 条件函数,返回 True 表示继续等待
            timeout: 超时时间 (秒)

        Returns:
            1 如果条件满足, 0 如果超时
        """
        return common_wait_fig(predicate=f, timeout=timeout, get_screen=self.get_screen)

    # ===== 坐标计算 =====

    def get_point(self, x: int, y: int):
        """打印坐标点的浮点表示 (用于调试)."""
        return common_debug_print_point(
            x=x,
            y=y,
            x1=self.x1,
            y1=self.y1,
            window_width=self.xx,
            window_height=self.yy,
            print_func=print,
        )

    def calc_point(
        self, point: Tuple[float, float], offset: Tuple[float, float]
    ) -> Tuple[float, float]:
        """把像素偏移量换算成归一化坐标的偏移并应用."""
        return common_calc_point(
            point=point,
            offset=offset,
            window_width=self.xx,
            window_height=self.yy,
        )

    # ===== 点击操作 =====

    def click(self, points: Tuple[float, float], click: int = 1):
        """点击一个点.

        Args:
            points: 归一化坐标 (x_ratio, y_ratio)
            click: 是否执行点击 (1=是, 0=只移动)
        """
        return common_click(
            points=points,
            click_enabled=bool(click),
            debug_level=0,
            print_func=print,
            print_stack=self.print_stack,
            x1=self.x1,
            y1=self.y1,
            window_width=self.xx,
            window_height=self.yy,
            is_fullscreen=bool(self.full),
            stop_flag=lambda: self._stop,
        )

    def click_box(self, box):
        """点击一个 box 的中心点."""
        return common_click_box(
            box=box,
            window_width=self.xx,
            window_height=self.yy,
            click=self.click,
        )

    def click_position(self, position: Tuple[float, float]):
        """点击一个像素坐标位置."""
        return common_click_position(
            position=position,
            window_width=self.xx,
            window_height=self.yy,
            click=self.click,
        )

    def drag(self, pt1: Tuple[float, float], pt2: Tuple[float, float]):
        """拖动操作."""
        return common_drag(
            start=pt1,
            end=pt2,
            x1=self.x1,
            y1=self.y1,
            window_width=self.xx,
            window_height=self.yy,
            is_fullscreen=bool(self.full),
        )

    # ===== 视觉函数 =====

    def scan_screenshot(self, prepared):
        """返回图片匹配结果."""
        return common_scan_screenshot(prepared)

    def calculated(self, result, shape):
        """计算匹配中心点坐标."""
        return common_calculated(result, shape)

    def click_target(self, target_path: str, threshold: float, flag: bool = True):
        """点击与模板匹配的点.

        Args:
            target_path: 模板图片路径
            threshold: 匹配阈值
            flag: True 表示必须匹配
        """

        def _on_found(points, _result, template):
            self.get_point(*points)
            if self.log:
                self.log.info(f"target shape: {template.shape}")

        common_click_target(
            target_path=target_path,
            threshold=threshold,
            must_match=bool(flag),
            print_func=print,
            on_found=_on_found,
            exit_on_found=False,
        )

    # ===== 截图函数 =====

    def get_local(
        self, x: float, y: float, size: Tuple[int, int], large: bool = True
    ) -> "ndarray":
        """在截图中裁剪需要匹配的部分."""
        return common_get_local(
            screen=self.screen,
            window_width=self.xx,
            window_height=self.yy,
            x_ratio=x,
            y_ratio=y,
            size=(size[0], size[1]),
            large=bool(large),
        )

    def get_screen(self) -> "ndarray":
        """从全屏截屏中裁剪得到游戏窗口截屏."""
        import win32gui

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)

        while not is_game_window(title) and not self._stop:
            if self.log:
                self.log.warning("等待游戏窗口")
            time.sleep(0.5)
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)

        self.screen = self.sct.grab(self.x0, self.y0)
        return self.screen

    # ===== 模板匹配 =====

    def check(
        self,
        path: str,
        x: float,
        y: float,
        mask: Optional[str] = None,
        threshold: Optional[float] = None,
        large: bool = True,
    ):
        """判断截图中匹配中心点附近是否存在匹配模板.

        Args:
            path: 匹配模板的路径 (不含扩展名)
            x, y: 匹配中心点 (归一化坐标)
            mask: 掩码模板名称
            threshold: 匹配阈值
            large: 是否返回匹配结果 (False 返回局部截图)

        Returns:
            large=True: 是否匹配成功
            large=False: 局部截图
        """
        if threshold is None:
            threshold = self.threshold

        formatted_target_path = self.format_path(path)
        target = cv.imread(formatted_target_path)

        # F 键图片阈值微调
        if formatted_target_path.endswith("f.jpg"):
            threshold -= 0.01

        match = match_template_near_point(
            cv=cv,
            screen=self.screen,
            read_image=cv.imread,
            format_path=self.format_path,
            get_local=lambda x_ratio, y_ratio, size, large_flag: self.get_local(
                x_ratio, y_ratio, size, large_flag
            ),
            path=path,
            x_ratio=x,
            y_ratio=y,
            scx=float(self.scx),
            threshold=float(threshold),
            mask=mask,
            large=bool(large),
            target_image=target,
        )

        if not large:
            return match.local_screen

        self.tx = match.tx
        self.ty = match.ty
        self.tm = match.max_val

        if match.max_val > threshold:
            if self.last_info != formatted_target_path and self.log:
                self.log.info(
                    "匹配到图片 %s 相似度 %f 阈值 %f"
                    % (formatted_target_path, match.max_val, threshold)
                )
            self.last_info = formatted_target_path

        return match.matched

    # ===== 小地图操作 =====

    def exist_minimap(self):
        """初步裁剪小地图,并增强小地图中的蓝色箭头."""
        self.loc_scr = common_exist_minimap(
            get_screen=self.get_screen,
            get_local=lambda x, y, size, large=True: self.get_local(x, y, size, large),
            scx=float(self.scx),
        )

    def take_fine_minimap(self, n: int = 5, dt: float = 0.01, dy: int = 200):
        """移动视角,获得小地图中不变的部分 (白线, 灰块)."""
        return common_take_fine_minimap(
            get_screen=self.get_screen,
            exist_minimap_fn=lambda: (self.exist_minimap() or self.loc_scr),
            n=n,
            dt=dt,
            dy=dy,
        )

    def get_now_direc(self, loc_scr: "ndarray") -> float:
        """计算小地图中蓝色箭头的角度."""
        return common_get_now_direc(
            cv=cv,
            loc_scr=loc_scr,
            arrow_template_path=self.format_path("loc_arrow"),
        )

    def get_bw_map(
        self, gs: int = 1, local_screen: Optional["ndarray"] = None
    ) -> Optional["ndarray"]:
        """获取小地图的黑白格式.

        Args:
            gs: 是否重新截图
            local_screen: 可选的预截图

        Returns:
            黑白格式的小地图,如果在祝福选择界面返回 None
        """
        shape = (int(self.scx * 190), int(self.scx * 190))

        if gs:
            self.get_screen()
            if self.check("choose_blessing", UICoords.CHOOSE_BLESSING_X, UICoords.CHOOSE_BLESSING_Y):
                return None

        if local_screen is None:
            local_screen = self.get_local(
                MinimapCoords.CENTER_X_RATIO, MinimapCoords.CENTER_Y_RATIO, shape
            )

        # 计算阈值
        gray_threshold = (
            ColorThresholds.MINIMAP_GRAY_BASE
            + self.find * ColorThresholds.MINIMAP_GRAY_FIND_BONUS
        )
        black_threshold = (
            ColorThresholds.MINIMAP_BLACK_BASE
            + self.find * ColorThresholds.MINIMAP_BLACK_FIND_BONUS
        )
        white_threshold = (
            ColorThresholds.MINIMAP_WHITE_BASE
            + self.find * ColorThresholds.MINIMAP_WHITE_FIND_BONUS
        )

        bw_map = np.zeros(local_screen.shape[:2], dtype=np.uint8)

        # 灰块检测
        b_map = deepcopy(bw_map)
        b_map[np.sum((local_screen - Colors.GRAY) ** 2, axis=-1) <= gray_threshold] = (
            255
        )

        # 黑色区域检测
        blk_map = deepcopy(bw_map)
        blk_map[
            np.sum((local_screen - Colors.BLACK) ** 2, axis=-1) <= black_threshold
        ] = 255

        # 形态学操作
        kernel_9 = np.ones((9, 9), np.uint8)
        cv.dilate(blk_map, kernel_9, iterations=1)

        kernel_5 = np.ones((5, 5), np.uint8)
        b_map = cv.dilate(b_map, kernel_5, iterations=1)

        # 白线检测
        bw_map[
            (np.sum((local_screen - Colors.WHITE_210) ** 2, axis=-1) <= white_threshold)
            & (b_map > 200)
        ] = 255

        # 裁剪
        if self.find == 0:
            bw_map = bw_map[
                int(shape[0] * 0.5) - 68 : int(shape[0] * 0.5) + 108,
                int(shape[1] * 0.5) - 48 : int(shape[1] * 0.5) + 128,
            ]
        else:
            bw_map = bw_map[
                int(shape[0] * 0.5) - 68 - 2 : int(shape[0] * 0.5) + 108 - 2,
                int(shape[1] * 0.5) - 48 - 8 : int(shape[1] * 0.5) + 128 - 8,
            ]

        # 应用圆形掩码
        for i in range(bw_map.shape[0]):
            for j in range(bw_map.shape[1]):
                if ((i - 88) ** 2 + (j - 88) ** 2) > 85**2:
                    bw_map[i, j] = 0

        return bw_map

    # ===== 鼠标移动 =====

    def mouse_move(self, x: float, fine: int = 1):
        """视角转动 x 度.

        Args:
            x: 旋转角度
            fine: 精度参数
        """
        max_angle = MouseParams.MAX_ANGLE_PER_MOVE // fine

        if x > max_angle:
            y = max_angle
        elif x < -max_angle:
            y = -max_angle
        else:
            y = x

        dx = int(MouseParams.ANGLE_TO_PIXEL * y * self.multi * self.scale)

        if self._stop == 0 and self.stop_move == 0:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, 0)

        time.sleep(MouseParams.MOVE_DELAY * fine)

        if x != y:
            if self._stop == 0:
                self.mouse_move(x - y, fine)
            else:
                raise ValueError("正在退出")

    # ===== 图像旋转 =====

    def handle_rotate_val(
        self, x: int, y: int, rotate: float
    ) -> "ndarray":
        """计算旋转变换矩阵."""
        cos_val = np.cos(np.deg2rad(rotate))
        sin_val = np.sin(np.deg2rad(rotate))
        return np.float32(
            [
                [cos_val, sin_val, x * (1 - cos_val) - y * sin_val],
                [-sin_val, cos_val, x * sin_val + y * (1 - cos_val)],
            ]
        )

    def image_rotate(self, src: "ndarray", rotate: float = 0) -> "ndarray":
        """图像旋转 (以中心点为中心)."""
        h, w, c = src.shape
        M = self.handle_rotate_val(w // 2, h // 2, rotate)
        return cv.warpAffine(src, M, (w, h))

    # ===== 特征匹配 =====

    def extract_features(self, img: "ndarray") -> Optional["ndarray"]:
        """提取 ORB 特征描述符."""
        return extract_orb_features(img, border=50)

    def match_two(self, img1: "ndarray", img2: "ndarray") -> float:
        """匹配两张图片的相似度."""
        key1 = self.extract_features(img1)
        key2 = self.extract_features(img2)
        similarity = match_features(key1, key2)
        if self.log:
            self.log.info(f"相似度:{similarity}")
        return similarity

    # ===== 距离计算 =====

    def get_dis(
        self, x: Tuple[float, float], y: Tuple[float, float]
    ) -> float:
        """计算两点间的欧几里得距离."""
        return euclidean_distance(x, y)

    def get_offset(self, delta: int = 1) -> Tuple[float, float]:
        """计算基于当前角度的偏移量."""
        pi = 3.141592653589
        dx, dy = sin(self.ang / 180 * pi), cos(self.ang / 180 * pi)
        return (delta * dx * 3, delta * dy * 3)

    def get_real_loc(self, delta: int = 0):
        """根据当前位置和角度计算真实位置."""
        x, y = self.now_loc
        dx, dy = self.get_offset(delta=delta)
        self.real_loc = (int(x + 10 + dx), int(y + dy))

    # ===== 状态检测 =====

    def check_auto(self) -> bool:
        """检测是否开启自动战斗."""
        auto = self.check(
            "z",
            UICoords.AUTO_BATTLE_X,
            UICoords.AUTO_BATTLE_Y,
            large=False,
            mask="mask_auto",
        )
        return check_auto_battle(auto)

    def isrun(self) -> bool:
        """检测角色是否在跑步状态."""
        scr = self.screen
        shape = (int(self.scx * 12), int(self.scx * 12))
        loc_scr = self.get_local(
            MinimapCoords.CENTER_X_RATIO, MinimapCoords.CENTER_Y_RATIO, shape
        )

        is_running, mask_sum = check_running_state(loc_scr)

        scr_bak = deepcopy(scr)
        scr[np.min(scr, axis=-1) <= 220] = [0, 0, 0]
        scr[np.min(scr, axis=-1) > 220] = [255, 255, 255]

        res = (
            self.check("run", UICoords.RUN_X, UICoords.RUN_Y, threshold=MatchThresholds.RUNNING)
            and is_running
        )

        if self.tm > 0.96:
            res = True

        self.screen = deepcopy(scr_bak)

        if res:
            self.f_time = 0

        return res

    # ===== 调试工具 =====

    def print_stack(self, num: int = 1, force: int = 0):
        """打印调用栈信息 (用于调试).

        Args:
            num: 要打印的栈帧数量
            force: 是否强制打印
        """
        if force:
            stk = traceback.extract_stack()
            for i in range(num):
                try:
                    print(
                        stk[-2].name,
                        stk[-3 - i].filename.split("\\")[-1].split(".")[0],
                        stk[-3 - i].name,
                        stk[-3 - i].lineno,
                    )
                except IndexError:
                    break
