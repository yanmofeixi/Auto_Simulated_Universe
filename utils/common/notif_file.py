"""notif.txt 文件读写工具.

该仓库使用 `logs/notif.txt` 作为“通知插件(notif.exe / notif.py)”与
自动化脚本(diver/simul)之间的轻量 IPC.

文件约定(历史兼容):
- 第 1 行:cnt(通关计数,字符串但通常是整数)
- 第 2 行:title(通知标题)
- 第 3 行:msg(通知正文)
- 第 4 行:tm(写入时间戳,字符串;缺失或非法时允许回退)

注意:
- 这里不做“周刷新计数”的业务逻辑(那由 utils/common/run_counter.py 负责).
- 本模块只负责尽量兼容地读写 notif.txt.
"""

from __future__ import annotations

import os
import time
from typing import Optional, Tuple


def _read_existing_cnt_and_tm(file_name: str) -> Tuple[Optional[str], Optional[str]]:
    """尽量从现有文件中读取 (cnt, tm).

    返回值允许为 None:调用方应自行提供默认值.
    """

    if not os.path.exists(file_name):
        return None, None

    try:
        with open(file_name, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        cnt = lines[0].strip("\n") if len(lines) >= 1 else None
        tm = lines[3].strip("\n") if len(lines) >= 4 else None
        return cnt or None, tm or None
    except Exception:
        return None, None


def write_notif_file(
    *,
    title: str,
    msg: str,
    cnt: Optional[str] = None,
    tm: Optional[str] = None,
    file_name: str = "logs/notif.txt",
) -> int:
    """写入 notif.txt 并返回解析后的 cnt(失败则为 0).

    兼容策略(与历史实现保持一致):
    - 若 cnt=None:尝试沿用旧文件的 cnt,否则默认为 "0".
    - 若 tm=None:尝试沿用旧文件的 tm,否则默认为当前 time.time().
    - 若 cnt 明确给出:默认把 tm 设为当前时间(代表一次“有效刷新”).
    """

    os.makedirs(os.path.dirname(file_name) or ".", exist_ok=True)

    # 与历史行为一致:传了 cnt 就意味着刷新时间应更新
    if cnt is not None and tm is None:
        tm = str(time.time())

    existing_cnt, existing_tm = _read_existing_cnt_and_tm(file_name)
    if cnt is None:
        cnt = existing_cnt
    if tm is None:
        tm = existing_tm

    if cnt is None:
        cnt = "0"
    if tm is None:
        tm = str(time.time())

    try:
        with open(file_name, "w", encoding="utf-8") as fh:
            fh.write(f"{cnt}\n{title}\n{msg}\n{tm}")
    except Exception:
        # 写入失败时也返回一个合理的整数
        pass

    try:
        return int(cnt)
    except Exception:
        return 0


def read_notif_file(*, file_name: str = "logs/notif.txt") -> Tuple[str, str, str, str]:
    """读取 notif.txt 的四行内容.

    返回 (cnt, title, msg, tm).任何缺失行会被置为空字符串.
    """

    if not os.path.exists(file_name):
        return "", "", "", ""

    try:
        with open(file_name, "r", encoding="utf-8", errors="ignore") as fh:
            lines = [line.rstrip("\n") for line in fh.readlines()]
        while len(lines) < 4:
            lines.append("")
        return lines[0], lines[1], lines[2], lines[3]
    except Exception:
        return "", "", "", ""
