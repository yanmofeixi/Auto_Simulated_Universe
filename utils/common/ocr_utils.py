"""OCR 工具函数模块.

该模块提供 OCR 相关的通用工具函数,包括:
- 编辑距离计算
- 文本相似度判断
- OCR 结果处理

供 simul 和 diver 的 OCR 模块复用.
"""

from __future__ import annotations

from functools import cmp_to_key
from typing import Any, List, Optional


def is_edit_distance_at_most_n(str1: str, str2: str, ch: str, max_diff: int = 1) -> int:
    """判断两个字符串的编辑距离是否不超过 n.

    该函数用于模糊匹配 OCR 识别结果,容忍多字符的识别错误.

    算法逻辑:
    1. 首先检查两个字符串的直接差异字符数
    2. 如果差异不超过 max_diff,返回匹配成功
    3. 否则尝试在 str2 末尾添加 ch 后再次比较(处理缺字情况)

    Args:
        str1: 目标字符串(期望的文本)
        str2: 待比较字符串(OCR 识别结果的子串)
        ch: 附加字符(用于处理边界情况)
        max_diff: 允许的最大差异字符数

    Returns:
        1 表示编辑距离不超过 max_diff,0 表示超过

    Example:
        >>> is_edit_distance_at_most_n("黄泉", "黄泉", "", 1)
        1
        >>> is_edit_distance_at_most_n("黄泉", "黄权", "", 1)
        1
        >>> is_edit_distance_at_most_n("寰宇热寂特征数", "寰宇热寂特微数", "", 2)
        1
    """
    length = len(str1)

    # 直接比较差异字符数
    diff_count = sum(1 for i in range(length) if str1[i] != str2[i])
    if diff_count <= max_diff:
        return 1

    # 尝试添加字符后比较(处理缺字情况)
    i = 0
    j = 0
    diff_count = 0
    str2 += ch

    while i < length and j < length + 1:
        if str1[i] != str2[j]:
            diff_count += 1
            j += 1
        else:
            i += 1
            j += 1

    return 1 if diff_count <= max_diff else 0


def is_edit_distance_at_most_one(str1: str, str2: str, ch: str) -> int:
    """判断两个字符串的编辑距离是否不超过 1.

    该函数用于模糊匹配 OCR 识别结果,容忍单字符的识别错误.
    这是 is_edit_distance_at_most_n 的特化版本,保持向后兼容.

    Args:
        str1: 目标字符串(期望的文本)
        str2: 待比较字符串(OCR 识别结果的子串)
        ch: 附加字符(用于处理边界情况)

    Returns:
        1 表示编辑距离不超过 1,0 表示超过
    """
    return is_edit_distance_at_most_n(str1, str2, ch, max_diff=1)


def get_max_diff_by_length(length: int) -> int:
    """根据文本长度计算允许的最大差异字符数.

    规则:
    - 长度 >= 7: 允许 3 个字的误差
    - 长度 >= 5: 允许 2 个字的误差
    - 其他: 允许 1 个字的误差

    Args:
        length: 文本长度

    Returns:
        允许的最大差异字符数
    """
    if length >= 7:
        return 3
    elif length >= 5:
        return 2
    else:
        return 1


def fuzzy_match(target: str, text: str) -> bool:
    """模糊匹配目标文本是否出现在文本中.

    使用编辑距离容忍识别错误,误差容忍度根据目标文本长度动态调整:
    - 长度 >= 7: 允许 3 个字的误差
    - 长度 >= 5: 允许 2 个字的误差
    - 其他: 允许 1 个字的误差

    Args:
        target: 目标文本
        text: 待搜索的文本

    Returns:
        True 如果找到匹配
    """
    # 特殊处理:某些短文本需要精确匹配
    text = text.strip()
    if target.strip() in ['胜军', '脊刺', '佩拉']:
        return target.strip() in text

    length = len(target)
    search_text = text + ' '
    max_diff = get_max_diff_by_length(length)

    for i in range(len(search_text) - length):
        if is_edit_distance_at_most_n(target, search_text[i:i + length], search_text[i + length], max_diff):
            return True

    return False


# 类型别名
OcrBox = List[int]  # [x1, x2, y1, y2]
OcrItem = dict[str, Any]


def sort_ocr_items(items: List[OcrItem]) -> List[OcrItem]:
    """对 OCR 识别结果按位置排序.

    按照从上到下,从左到右的顺序排列.
    同一行(y 坐标差 <= 7)的项目按 x 坐标排序.

    Args:
        items: OCR 识别结果列表

    Returns:
        排序后的列表
    """
    def compare(item1: OcrItem, item2: OcrItem) -> int:
        x1, _, y1, _ = item1['box']
        x2, _, y2, _ = item2['box']
        if abs(y1 - y2) <= 7:
            return x1 - x2
        return y1 - y2

    return sorted(items, key=cmp_to_key(compare))


def merge_ocr_items(items: List[OcrItem]) -> List[OcrItem]:
    """合并相邻的 OCR 识别结果.

    将同一行且水平相邻的文本框合并为一个.

    判断条件:
    - y 坐标差 <= 10(同一行)
    - x 坐标差 <= 35(相邻)

    Args:
        items: OCR 识别结果列表

    Returns:
        合并后的列表
    """
    if len(items) == 0:
        return items

    items = sort_ocr_items(items)
    result: List[OcrItem] = []
    merged: OcrItem = items[0].copy()

    for i in range(1, len(items)):
        current = items[i]
        # 判断是否应该合并
        same_line = abs(current['box'][2] - merged['box'][2]) <= 10
        same_height = abs(current['box'][3] - merged['box'][3]) <= 10
        adjacent = abs(current['box'][0] - merged['box'][1]) <= 35

        if same_line and same_height and adjacent:
            # 合并文本和边界框
            merged['raw_text'] += current['raw_text']
            merged['box'][1] = current['box'][1]
        else:
            result.append(merged)
            merged = current.copy()

    result.append(merged)
    return result
