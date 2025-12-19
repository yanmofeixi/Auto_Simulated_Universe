"""diver/simul 共享的应用级小工具.

目前抽离范围(低风险,收益高):
- notif:写入 logs/notif.txt 供通知插件读取
- set_forground:读取 config 并尝试将游戏窗口置前台

说明:
- 这里只做“薄封装”,不引入 diver/simul 的业务依赖.
- 通过参数注入(config/log/is_frozen)保持两侧行为一致.
"""

from __future__ import annotations

from typing import Optional

from utils.common.notif_file import write_notif_file
from utils.common.window import set_game_foreground


def notif(*, title: str, msg: str, cnt: Optional[str] = None, log=None) -> int:
    """写入通知文件并返回当前计数.

    Args:
        title: 通知标题.
        msg: 通知正文.
        cnt: 计数(可选).为 None 时会尽量沿用旧文件内容.
        log: logger(可选),用于保持历史日志输出.

    Returns:
        解析后的计数(int).
    """

    try:
        if log is not None:
            log.info("通知:" + msg + "  " + title)
    except Exception:
        pass

    return write_notif_file(title=title, msg=msg, cnt=None if cnt is None else str(cnt))


def set_forground(*, config, is_frozen: bool) -> None:
    """将游戏窗口设为前台(尽量兼容历史行为).

    Args:
        config: diver/simul 的 config 对象(需提供 read()).
        is_frozen: 是否为打包后的可执行环境(用于 SendKeys 行为兼容).
    """

    try:
        config.read()
    except Exception:
        # 与历史实现一致:读取失败也不阻断
        pass

    try:
        # 统一复用共享实现:内部会处理 SendKeys 解锁焦点 + 窗口查找与置前台
        set_game_foreground(is_frozen=is_frozen)
    except Exception:
        # 与历史实现一致:置前台失败时静默忽略
        pass
