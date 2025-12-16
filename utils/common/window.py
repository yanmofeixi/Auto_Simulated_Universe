"""Windows 窗口控制工具.

该模块封装 diver/simul 共用的"将游戏窗口设为前台"的逻辑.

注意:
- 该仓库主要运行在 Windows;本模块依赖 pywin32(win32gui 等).
- 为了减少导入副作用,win32com/pythoncom 在函数内延迟导入.
"""

from __future__ import annotations

from typing import Optional


def set_game_foreground(
    *,
    primary_title: str = "崩坏：星穹铁道",
    secondary_title: str = "云·星穹铁道",
    window_class: str = "UnityWndClass",
    is_frozen: bool = False,
) -> Optional[int]:
    """尝试将游戏窗口设为前台.

    返回:
    - 成功:窗口句柄(int)
    - 失败:None

    说明:
    - 与历史实现保持一致:通过 WScript.Shell.SendKeys 解除焦点锁定.
    - 若按 (class,title) 找不到,则回退到 (None,title).
    """

    try:
        # 延迟导入:避免模块级导入在某些环境出错
        import pythoncom
        import win32com.client
        import win32gui

        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys(" " if is_frozen else "")

        # 尝试用 class + title 查找
        hwnd = win32gui.FindWindow(window_class, primary_title)

        if hwnd == 0:
            # 回退：只用 title 查找
            hwnd = win32gui.FindWindow(None, secondary_title)

        if hwnd == 0:
            return None

        # 找到窗口，尝试设为前台
        win32gui.SetForegroundWindow(hwnd)
        return int(hwnd)

    except Exception:
        return None
