"""通用文本处理工具(diver/simul 共享).

当前抽离范围(低风险):
- 文本清洗(移除常见符号)
- OCR box 文本合并与清洗
- 简单的类型前缀匹配(用于事件/区域类型识别)

说明:
- diver 侧原实现位于 utils/diver/text_utils.py;此处作为共享源.
- 为兼容历史导入路径,utils/diver/text_utils.py 将作为薄壳 re-export.
"""

from __future__ import annotations

from typing import Iterable, Optional


def clean_text(text: str, char: int = 1) -> str:
    """清洗文本,移除常见符号.

    Args:
        text: 原始文本.
        char: 是否额外移除 ASCII 数字与字母.

    Returns:
        清洗后的文本.
    """

    symbols = (
        r"[!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~-“”‘’«»„....¿¡£¥€©®™°±÷×¶§‰]"
        ",.!?;:()[]""<>,$ "
    )
    if char:
        symbols += r"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    translator = str.maketrans("", "", symbols)
    return text.translate(translator)


def merge_text(ts, text_items: Iterable[dict], char: int = 1) -> str:
    """合并 OCR box 文本并清洗.

    Args:
        ts: OCR 引擎对象(需提供 `sort_text()`).
        text_items: 形如 {'raw_text': str, ...} 的 iterable.
        char: 是否额外移除 ASCII 数字与字母.

    Returns:
        合并并清洗后的文本.
    """

    merged = "".join(
        item.get("raw_text", "") for item in ts.sort_text(list(text_items))
    )
    return clean_text(merged, char=char)


def get_text_type(text: str, types: Iterable[str], prefix: int = 1) -> Optional[str]:
    """在 text 中通过前缀匹配找到 types 里最先命中的类型字符串."""

    for type_name in types:
        if type_name[:prefix] in text:
            return type_name
    return None


__all__ = ["clean_text", "merge_text", "get_text_type"]
