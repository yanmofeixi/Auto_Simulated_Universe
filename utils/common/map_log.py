"""地图日志模块."""

from __future__ import annotations

import time
from logging import INFO, FileHandler, Formatter, getLogger

from utils.log import logs_path


def _build_logger():
    logger = getLogger("map_logger")
    logger.setLevel(INFO)

    logging_format = "[%(levelname)s] [%(asctime)s] %(message)s"

    # 根据日期生成日志文件名
    filename = logs_path / (
        "log_" + time.strftime("%Y-%m-%d-%H-%M", time.localtime()) + ".txt"
    )

    # 避免重复添加 handler(多次导入时会重复写入)
    if not any(isinstance(h, FileHandler) and getattr(h, "baseFilename", "") == str(filename) for h in logger.handlers):
        file_handler = FileHandler(filename=filename, mode="w", encoding="utf-8")
        file_handler.setFormatter(Formatter(logging_format))
        logger.addHandler(file_handler)

    return logger


map_log = _build_logger()
