"""通关计数(周刷新)工具.

该模块封装 diver/simul 共用的通关计数读写与“每周重置”逻辑.
"""

from __future__ import annotations

import datetime
import os
import time
from typing import Optional, Tuple

import pytz


def _read_count_file(file_name: str) -> Tuple[int, float]:
    """读取计数文件中的 (count, time_cnt).

    约定:
    - 第 1 行为 count
    - 第 4 行为 time_cnt(历史写入的浮点秒时间戳)
    - 若解析失败则回退到文件 mtime
    """

    new_cnt = 0
    time_cnt = os.path.getmtime(file_name)
    try:
        with open(file_name, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        try:
            new_cnt = int(lines[0].strip("\n"))
            time_cnt = float(lines[3].strip("\n"))
        except Exception:
            # 保持兼容:文件格式不完整时退回 mtime
            pass
    except Exception:
        pass

    return new_cnt, time_cnt


def _ensure_count_file(file_name: str) -> float:
    """确保计数文件存在,返回其 mtime."""

    os.makedirs(os.path.dirname(file_name) or ".", exist_ok=True)
    if not os.path.exists(file_name):
        with open(file_name, "w", encoding="utf-8") as fh:
            fh.write("0")
    return os.path.getmtime(file_name)


def _resolve_timezone(timezone: str):
    """将配置里的时区枚举映射为 tzinfo."""

    tz_dict = {
        "Default": None,
        "America": pytz.timezone("US/Central"),
        "Asia": pytz.timezone("Asia/Shanghai"),
        "Europe": pytz.timezone("Europe/London"),
    }
    return tz_dict.get(timezone)


def compute_weekly_count(
    *,
    new_cnt: int,
    time_cnt: float,
    timezone: str,
    read_mode: bool,
    now: Optional[datetime.datetime] = None,
) -> int:
    """按“每周一 04:00(按配置时区)”规则计算本周计数."""

    dt = now or datetime.datetime.now().astimezone()
    tz_info = _resolve_timezone(timezone)
    if tz_info is not None:
        dt = dt.astimezone(tz_info)

    current_weekday = dt.weekday()
    monday = dt + datetime.timedelta(days=-current_weekday)
    target_datetime = datetime.datetime(
        monday.year, monday.month, monday.day, 4, 0, 0, tzinfo=tz_info
    )
    monday_ts = target_datetime.timestamp()

    if dt.timestamp() >= monday_ts and time_cnt < monday_ts:
        # 新的一周:read_mode=True 时应重置为 0;read_mode=False(本次完成)则为 1
        return int(not read_mode)

    return int(new_cnt)


def update_weekly_counter(
    *,
    file_name: str = "logs/notif.txt",
    timezone: str,
    read_mode: bool,
    current_count: int,
    current_count_tm: float,
) -> Tuple[int, float]:
    """统一的“读/写通关计数”逻辑.

    返回:
    - count: 更新后的计数
    - count_tm: 更新后的本地更新时间(time.time())
    """

    if read_mode:
        _ensure_count_file(file_name)
        new_cnt, time_cnt = _read_count_file(file_name)
    else:
        new_cnt = int(current_count) + 1
        time_cnt = float(current_count_tm)

    count = compute_weekly_count(
        new_cnt=new_cnt,
        time_cnt=time_cnt,
        timezone=timezone,
        read_mode=read_mode,
    )

    return count, time.time()
