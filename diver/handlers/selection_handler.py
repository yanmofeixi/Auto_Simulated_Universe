"""差分宇宙:选择处理器 (selection_handler).

该模块负责各类选择界面的识别与处理:
- 普通祝福 (blessing): 祝福选择时触发
- 方程选择 (equation): 方程选择时触发
- 金血祝福 (boon): 金血祝福选择
- 奇物 (curio): 奇物选择
- 加权奇物 (weighted_curio): 加权奇物选择
- 丢弃祝福 (drop_blessing): 选择分数最低的祝福丢弃

核心流程:
1. 构建候选列表
2. 使用对应的打分函数进行评分
3. 按分数排序后点击选择
"""

from __future__ import annotations

import time

from utils.log import log, my_print as print


def _find_choice_text(universe):
    """获取选择候选区域的 OCR 文本块.

    Returns:
        (bottom_text, text): bottom_text 是屏幕下方识别的文字(用于打印),
                             text 是实际使用的文字(可能来自下方或中间)
    """

    # 屏幕下方(祝福位置上下浮动,故加大识别区域)
    # OCR box [350, 1550, 750, 900] 在 1920x1080 屏幕上的位置:
    # ┌──────────────────────────────────────┐
    # │                                      │
    # │                                      │
    # │                                      │
    # │                                      │
    # │                                      │
    # │                                      │
    # │                                      │
    # │  ┌────────────────────────────────┐  │  y=750
    # │  │     祝福名称/选项文字区域          │  │
    # │  │      (x: 350~1550)             │  │
    # │  └────────────────────────────────┘  │  y=900
    # └──────────────────────────────────────┘
    bottom_text = universe.ts.find_with_box([350, 1550, 750, 900])
    text = bottom_text
    if len(text) == 0:
        # 屏幕中间(祝福名称)
        # OCR box [350, 1550, 480, 530] 在 1920x1080 屏幕上的位置:
        # ┌──────────────────────────────────────┐
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │  ┌────────────────────────────────┐  │  y=480
        # │  │     祝福名称 (窄条区域)           │  │
        # │  └────────────────────────────────┘  │  y=530
        # │                                      │
        # │                                      │
        # │                                      │
        # └──────────────────────────────────────┘
        text = universe.ts.find_with_box([350, 1550, 480, 530])
    return bottom_text, text


def _find_weighted_curio_text(universe):
    """获取加权奇物选择候选区域的 OCR 文本块.

    加权奇物优先检测屏幕中间区域,然后再检测靠下区域.

    Returns:
        (middle_text, text): middle_text 是屏幕中间识别的文字(用于打印),
                             text 是实际使用的文字(来自中间或下方)
    """
    # 屏幕中间区域 (加权奇物名称)
    # OCR box [285, 1682, 483, 549] 在 1920x1080 屏幕上的位置:
    # ┌──────────────────────────────────────┐
    # │                                      │
    # │                                      │
    # │                                      │
    # │                                      │
    # │  ┌──────────────────────────────────┐│  y=483
    # │  │   加权奇物名称 (x: 285~1682)       ││
    # │  └──────────────────────────────────┘│  y=549
    # │                                      │
    # │                                      │
    # │                                      │
    # └──────────────────────────────────────┘
    middle_text = universe.ts.find_with_box([285, 1682, 483, 549])
    text = middle_text

    if len(text) == 0:
        # 屏幕中间区域 + 靠下区域
        # OCR box [289, 1682, 483, 832] 在 1920x1080 屏幕上的位置:
        # ┌──────────────────────────────────────┐
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │  ┌──────────────────────────────────┐│  y=483
        # │  │                                  ││
        # │  │   加权奇物名称+描述区域             ││
        # │  │   (x: 289~1682)                  ││
        # │  │                                  ││
        # │  └──────────────────────────────────┘│  y=832
        # │                                      │
        # └──────────────────────────────────────┘
        text = universe.ts.find_with_box([289, 1682, 483, 832])

    return middle_text, text


def _build_candidates(universe, text, score_fn, fallback_score_fn=None):
    """将 OCR 文本块转换为可打分的候选列表.

    Args:
        universe: 差分宇宙实例
        text: OCR 文本块列表
        score_fn: 打分函数,接受文本返回分数
        fallback_score_fn: 备用打分函数,当主打分函数返回 0 时使用 (可选)

    Returns:
        候选列表 [{name, box, score, x}, ...]
    """

    candidates = []
    for item in text:
        orig_box = item["box"]
        name = item.get("raw_text", "")  # 原始识别的文字(名称)
        x = (orig_box[0] + orig_box[1]) // 2  # 用于排序的 x 坐标
        box = [x - 220, x + 220, 450, 850]  # 扩展后的区域

        choice_text = universe.ts.find_with_box(box)
        choice_raw_text = universe.merge_text(choice_text, char=0)
        score = score_fn(choice_raw_text)

        # 如果主打分为 0 且有备用打分函数,使用备用打分
        if score == 0 and fallback_score_fn:
            score = fallback_score_fn(choice_raw_text)

        candidates.append(
            {
                "name": name,
                "box": box,
                "score": score,
                "x": x,
            }
        )
    return candidates


def _print_bottom_text(bottom_text, candidates):
    """按从左到右顺序打印屏幕下方识别的文字及其对应的分数.

    Args:
        bottom_text: 屏幕下方识别的 OCR 文本块
        candidates: 候选列表 (用于获取分数)
    """
    if not bottom_text:
        return

    # 按 x 坐标排序
    sorted_bottom = sorted(
        bottom_text, key=lambda item: (item["box"][0] + item["box"][1]) // 2
    )

    # 构建 name -> score 的映射
    score_map = {c["name"]: c["score"] for c in candidates}

    display = []
    for item in sorted_bottom:
        name = item.get("raw_text", "")
        score = score_map.get(name, 0)
        display.append((name, score))

    print(display)


def _print_middle_text(middle_text, candidates):
    """按从左到右顺序打印屏幕中间识别的文字及其对应的分数.

    专用于加权奇物的日志输出.

    Args:
        middle_text: 屏幕中间识别的 OCR 文本块
        candidates: 候选列表 (用于获取分数)
    """
    if not middle_text:
        log.info("加权奇物中间区域未识别到文字")
        return

    # 按 x 坐标排序 (从左到右)
    sorted_middle = sorted(
        middle_text, key=lambda item: (item["box"][0] + item["box"][1]) // 2
    )

    # 构建 name -> score 的映射
    score_map = {c["name"]: c["score"] for c in candidates}

    display = []
    for item in sorted_middle:
        name = item.get("raw_text", "")
        score = score_map.get(name, 0)
        display.append((name, score))

    log.info(f"加权奇物中间区域文字(从左到右): {display}")


def _click_choice(universe, box, confirm_boon: bool = False) -> None:
    """点击选择并确认.

    Args:
        universe: 差分宇宙实例
        box: 选择区域的边界框
        confirm_boon: 是否为金血祝福确认 (金血祝福确认按钮位置不同)
    """

    if not universe.click_img("new"):
        universe.click_position([(box[0] + box[1]) // 2, 500])

    if confirm_boon:
        universe.click_position([960, 975])
    else:
        universe.click_position([1695, 962])

    time.sleep(1)


def _handle_selection(
    universe,
    update_prior_fn,
    score_fn,
    reverse: bool = True,
    confirm_boon: bool = False,
    fallback_score_fn=None,
) -> None:
    """通用选择处理逻辑.

    Args:
        universe: 差分宇宙实例
        update_prior_fn: 更新优先级表的函数
        score_fn: 打分函数
        reverse: 是否按分数降序排序 (True=降序选最高, False=升序选最低)
        confirm_boon: 是否为金血祝福确认
        fallback_score_fn: 备用打分函数,当主打分函数返回 0 时使用 (可选)
    """

    universe.blessing_solved = 1

    bottom_text, text = _find_choice_text(universe)
    if len(text) == 0:
        return

    update_prior_fn()

    # 如果有 fallback,同时更新 other 优先级表
    if fallback_score_fn:
        universe.update_other_prior()

    candidates = _build_candidates(universe, text, score_fn, fallback_score_fn)
    _print_bottom_text(bottom_text, candidates)

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=reverse)
    box = candidates[0]["box"]
    _click_choice(universe, box, confirm_boon=confirm_boon)


# ==================== 公开 API ====================


def handle_blessing(universe, reverse: int = 1, boon: int = 0) -> None:
    """处理普通祝福选择.

    Args:
        universe: 差分宇宙实例
        reverse: 是否按分数降序排序 (1=降序选最高, 0=升序选最低)
        boon: 是否为金血祝福选择 (1=金血祝福, 0=普通祝福)

    Note:
        此函数保留以兼容旧代码,新代码请使用具体的 handle_* 函数.
    """
    _handle_selection(
        universe,
        update_prior_fn=universe.update_blessing_prior,
        score_fn=universe.blessing_score,
        reverse=bool(reverse),
        confirm_boon=bool(boon),
        fallback_score_fn=universe.other_score,
    )


def handle_drop_blessing(universe) -> None:
    """处理丢弃祝福 (选择分数最低的祝福).

    Args:
        universe: 差分宇宙实例
    """
    _handle_selection(
        universe,
        update_prior_fn=universe.update_blessing_prior,
        score_fn=universe.blessing_score,
        reverse=False,
        confirm_boon=False,
        fallback_score_fn=universe.other_score,
    )


def handle_equation(universe) -> None:
    """处理方程选择.

    Args:
        universe: 差分宇宙实例
    """
    _handle_selection(
        universe,
        update_prior_fn=universe.update_equation_prior,
        score_fn=universe.equation_score,
        reverse=True,
        confirm_boon=False,
        fallback_score_fn=universe.other_score,
    )


def handle_boon(universe) -> None:
    """处理金血祝福选择.

    如果所有候选的 score 都为 0,尝试点击刷新按钮刷新选项后再选择.

    Args:
        universe: 差分宇宙实例
    """
    universe.blessing_solved = 1

    bottom_text, text = _find_choice_text(universe)
    if len(text) == 0:
        return

    universe.update_boon_prior()
    universe.update_other_prior()

    candidates = _build_candidates(
        universe, text, universe.boon_score, universe.other_score
    )

    # 检查是否所有候选 score 都为 0
    all_zero = all(c["score"] == 0 for c in candidates)

    if all_zero:
        # 尝试点击刷新按钮
        log.info("金血祝福所有候选 score 为 0,尝试刷新选项")
        _print_bottom_text(bottom_text, candidates)
        # 刷新按钮区域 [650, 750, 900, 1000] 在 1920x1080 屏幕上的位置:
        # ┌──────────────────────────────────────┐
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │      ┌────┐                          │  y=900
        # │      │刷新│  (x: 650~750)            │
        # │      └────┘                          │  y=1000
        # └──────────────────────────────────────┘
        if not universe.click_img("divergent/refresh_boon"):
            # 找不到图片,直接点击坐标 (712, 965)
            universe.click_position([712, 965])

        time.sleep(0.8)

        # 重新截屏并刷新 OCR 缓存
        universe.ts.forward(universe.get_screen())

        # 重新识别
        bottom_text, text = _find_choice_text(universe)
        if len(text) == 0:
            return

        candidates = _build_candidates(
            universe, text, universe.boon_score, universe.other_score
        )

    _print_bottom_text(bottom_text, candidates)

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    box = candidates[0]["box"]
    _click_choice(universe, box, confirm_boon=True)


def handle_curio(universe) -> None:
    """处理奇物选择.

    Args:
        universe: 差分宇宙实例
    """
    _handle_selection(
        universe,
        update_prior_fn=universe.update_curio_prior,
        score_fn=universe.curio_score,
        reverse=True,
        confirm_boon=False,
        fallback_score_fn=universe.other_score,
    )


def handle_weighted_curio(universe) -> None:
    """处理加权奇物选择.

    加权奇物优先检测屏幕中间区域,然后再检测靠下区域.
    如果所有候选的 score 都为 0,尝试点击"覆写"按钮刷新选项后再选择.

    Args:
        universe: 差分宇宙实例
    """
    universe.blessing_solved = 1

    middle_text, text = _find_weighted_curio_text(universe)
    if len(text) == 0:
        return

    universe.update_weighted_curio_prior()
    universe.update_other_prior()

    candidates = _build_candidates(
        universe, text, universe.weighted_curio_score, universe.other_score
    )

    # 检查是否所有候选 score 都为 0
    all_zero = all(c["score"] == 0 for c in candidates)

    if all_zero:
        # 打印刷新前的候选
        _print_middle_text(middle_text, candidates)
        # 尝试在右下角寻找"覆写"文字并点击
        log.info("加权奇物所有候选 score 为 0,尝试点击覆写刷新选项")
        # 覆写按钮区域 [1100, 1500, 920, 1020] 在 1920x1080 屏幕上的位置:
        # ┌──────────────────────────────────────┐
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                                      │
        # │                    ┌──────────┐      │  y=920
        # │                    │  覆写    │      │
        # │                    │(x:1100~1500)    │
        # │                    └──────────┘      │  y=1020
        # └──────────────────────────────────────┘
        rewrite_text = universe.ts.find_with_box([1100, 1500, 920, 1020])
        clicked = False
        for item in rewrite_text:
            if "覆写" in item.get("raw_text", ""):
                box = item["box"]
                x, y = (box[0] + box[1]) // 2, (box[2] + box[3]) // 2
                universe.click_position([x, y])
                clicked = True
                break

        if not clicked:
            # 找不到文字,直接点击坐标 (1342, 979)
            universe.click_position([1342, 979])

        time.sleep(0.8)

        # 重新截屏并刷新 OCR 缓存
        universe.ts.forward(universe.get_screen())
        middle_text, text = _find_weighted_curio_text(universe)
        if len(text) == 0:
            return

        candidates = _build_candidates(
            universe, text, universe.weighted_curio_score, universe.other_score
        )

    # 打印最终的候选(刷新后或原始)
    _print_middle_text(middle_text, candidates)

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    box = candidates[0]["box"]
    _click_choice(universe, box, confirm_boon=False)
