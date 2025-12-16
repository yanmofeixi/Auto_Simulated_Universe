"""普通模拟宇宙:文本处理工具(兼容导出).

历史路径:utils/simul/text_utils.py
当前实现:复用 utils/common/text_utils.py,避免 diver/simul 重复维护.
"""

from __future__ import annotations

from utils.common.text_utils import clean_text, get_text_type, merge_text

__all__ = ["clean_text", "merge_text", "get_text_type"]
