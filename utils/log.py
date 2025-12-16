import logging
import io
import traceback
import os
from logging import (
    getLogger,
    StreamHandler,
    FileHandler,
    Formatter,
    basicConfig,
    INFO,
    DEBUG,
    CRITICAL,
)
from pathlib import Path
from datetime import datetime, timedelta

logs_path = Path("logs")
logs_path.mkdir(exist_ok=True, parents=True)

def clean_old_logs(days=7):
    """清理超过指定天数的日志文件,保留 log.txt, error_log.txt, notif.txt"""
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    keep_files = {"log.txt", "error_log.txt", "notif.txt"}
    
    for file in logs_path.iterdir():
        if file.name in keep_files:
            continue
        if file.name.startswith("log_") and file.suffix == ".txt":
            try:
                # 从文件名解析日期: log_YYYY-MM-DD-HH-MM.txt
                date_str = file.stem[4:]  # 去掉 "log_" 前缀
                file_date = datetime.strptime(date_str, "%Y-%m-%d-%H-%M")
                if file_date < cutoff:
                    file.unlink()
            except (ValueError, OSError):
                pass

# 启动时清理旧日志
clean_old_logs()

current_time_str = datetime.now().strftime("%Y-%m-%d-%H-%M")

log = getLogger()
log.setLevel(INFO)

logging_format = "%(levelname)s [%(asctime)s] [%(filename)s:%(lineno)d] %(message)s"
formatter = Formatter(logging_format)

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)

file_handler = FileHandler(filename=logs_path / "log.txt", mode="w", encoding="utf-8")
file_handler.setFormatter(formatter)

timestamped_file_handler = FileHandler(filename=logs_path / f"log_{current_time_str}.txt", mode="w", encoding="utf-8")
timestamped_file_handler.setFormatter(formatter)

log.addHandler(stream_handler)
log.addHandler(file_handler)
log.addHandler(timestamped_file_handler)

basicConfig(level=INFO)

def set_debug(debug: bool = False):
    log.setLevel(DEBUG if debug else INFO)

set_debug()

def my_print(*args, **kwargs):
    log.info(" ".join(map(str, args)))
    if len(kwargs):
        print(*args, **kwargs)

def print_exc():
    with io.StringIO() as buf, open("logs/error_log.txt", "a") as f:
        traceback.print_exc(file=buf)
        f.write(buf.getvalue())


# ========== 窗口调试日志 ==========
# 固定文件名，便于通过 git sync 获取调试信息

_WINDOW_DEBUG_LOG = logs_path / "window_debug.log"


def clear_window_debug_log():
    """清空窗口调试日志文件."""
    with open(_WINDOW_DEBUG_LOG, "w", encoding="utf-8") as f:
        f.write(f"=== 日志开始于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")


def log_debug(message: str) -> None:
    """写入窗口调试日志.

    Args:
        message: 日志消息
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_line = f"[{timestamp}] {message}\n"

    with open(_WINDOW_DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(log_line)
