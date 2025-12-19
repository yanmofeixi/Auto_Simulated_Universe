"""差分宇宙:OCR 识别与关键词词表."""

from __future__ import annotations

import time
from typing import Any, Iterable, Optional

import cv2 as cv
import numpy as np
from utils.common.ocr_utils import (
    is_edit_distance_at_most_one as _is_edit_distance_at_most_one,
    merge_ocr_items,
    OcrBox,
    OcrItem,
    sort_ocr_items,
)

from utils.onnxocr.onnx_paddleocr import ONNXPaddleOcr
from diver.config import config as diver_config


class My_TS:
    def __init__(self, lang: str = "ch", father: Any = None, use_gpu: bool | None = None):
        self.lang = lang
        # 如果未指定 use_gpu,则从配置文件读取
        if use_gpu is None:
            use_gpu = diver_config.ocr_use_gpu
        self.ts = ONNXPaddleOcr(use_angle_cls=False, cpu=not use_gpu, use_gpu=use_gpu)
        self.res: list[OcrItem] = []
        self.forward_img: Optional[np.ndarray] = None
        self.father = father

    def ocr_one_row(self, img: np.ndarray, box: Optional[OcrBox] = None) -> str:
        if box is None:
            result = self.ts.text_recognizer([img])[0][0]
        else:
            result = self.ts.text_recognizer([img[box[2] : box[3], box[0] : box[1]]])[
                0
            ][0]
        return result

    def is_edit_distance_at_most_one(self, str1, str2, ch):
        """检查两个字符串的编辑距离是否不超过1."""
        return _is_edit_distance_at_most_one(str1, str2, ch)

    def sort_text(self, text: list[OcrItem]) -> list[OcrItem]:
        """对 OCR 结果按位置排序."""
        return sort_ocr_items(text)

    def merge(self, text: list[OcrItem]) -> list[OcrItem]:
        """合并相邻的 OCR 识别结果."""
        return merge_ocr_items(text)

    def filter_non_white(self, image: np.ndarray, mode: int = 0) -> np.ndarray:
        if not mode:
            return image
        hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 160])
        upper_white = np.array([180, 40, 255])
        mask = cv.inRange(hsv_image, lower_white, upper_white)
        if mode == 1:
            filtered_image = cv.bitwise_and(image, image, mask=mask)
            return filtered_image
        elif mode == 2:
            lower_black = np.array([0, 0, 0])
            upper_black = np.array([180, 40, 50])
            mask_black = cv.inRange(hsv_image, lower_black, upper_black)
            kernel = np.ones((5, 30), np.uint8)
            mask_black = cv.dilate(mask_black, kernel, iterations=1)
            filtered_image = cv.bitwise_and(image, image, mask=mask & mask_black)
            return filtered_image

    def forward(self, img: np.ndarray) -> None:
        if (
            self.forward_img is not None
            and self.forward_img.shape == img.shape
            and np.sum(np.abs(self.forward_img - img)) < 1e-6
        ):
            return
        self.forward_img = img
        self.res = []
        ocr_res = self.ts.ocr(img)
        for res in ocr_res:
            res = {"raw_text": res[1][0], "box": np.array(res[0]), "score": res[1][1]}
            res["box"] = [
                int(np.min(res["box"][:, 0])),
                int(np.max(res["box"][:, 0])),
                int(np.min(res["box"][:, 1])),
                int(np.max(res["box"][:, 1])),
            ]
            self.res.append(res)
        self.res = self.merge(self.res)

    def find_with_text(self, text: Optional[Iterable[str]] = None) -> list[OcrItem]:
        """在已缓存的 OCR 结果中按文本匹配并返回候选项."""

        if text is None:
            text = []
        ans: list[OcrItem] = []
        for txt in text:
            for res in self.res:
                if res["raw_text"] in txt or txt in res["raw_text"]:
                    print("识别到文本:", txt, "匹配文本:", res.get("raw_text", ""))
                    ans.append({"text": txt, **res})
        return sorted(ans, key=lambda x: x.get("score", 0), reverse=True)

    def box_contain(
        self,
        box_out: OcrBox,
        box_in: OcrBox,
        redundancy: int | tuple[int, int] | list[int],
    ) -> bool:
        if isinstance(redundancy, (tuple, list)):
            r = redundancy
        else:
            r = (redundancy, redundancy)
        return (
            box_out[0] <= box_in[0] + r[0]
            and box_out[1] >= box_in[1] - r[0]
            and box_out[2] <= box_in[2] + r[1]
            and box_out[3] >= box_in[3] - r[1]
        )

    def find_with_box(
        self,
        box: Optional[OcrBox] = None,
        redundancy: int = 10,
        forward: int = 0,
        mode: int = 0,
    ) -> list[OcrItem]:
        if forward and box is not None:
            self.forward(
                self.filter_non_white(
                    self.father.get_screen()[box[2] : box[3], box[0] : box[1]],
                    mode=mode,
                )
            )

        ans: list[OcrItem] = []
        for res in self.res:
            if box is None:
                print(res["raw_text"], res["box"])
            elif forward == 0:
                if self.box_contain(box, res["box"], redundancy=redundancy):
                    ans.append(res)
            else:
                res["box"] = [
                    box[0] + res["box"][0],
                    box[0] + res["box"][1],
                    box[2] + res["box"][2],
                    box[2] + res["box"][3],
                ]
                ans.append(res)
        return self.sort_text(ans)


class text_keys:
    def __init__(self, fate: int = 4):
        self.fate = fate
        # 从 config 加载所有词表
        self.interacts = diver_config.get_interacts("diver")
        self.fates = diver_config.get_fates()
        self.prior_blessing = diver_config.get_prior_blessing()
        self.curio = diver_config.get_curio()
        self.blessings = diver_config.get_blessings_by_fate()
        self.secondary = diver_config.get_secondary_fates()

        # 从 config 读取用户配置,覆盖默认值
        data = diver_config.load_yaml()
        if data:
            prior = data.get("prior")
            try:
                secondary_override = data.get("config", {}).get("secondary_fate")
                if isinstance(secondary_override, list):
                    self.secondary = secondary_override
            except Exception:
                pass

            if isinstance(prior, dict):
                for i, key in enumerate(prior):
                    if i > 1:
                        self.blessings[i - 2] = prior[key]
                    elif i == 0:
                        self.curio = prior[key]

        self.prior_blessing += self.blessings[fate]
        self.skip = 1
        for s in self.prior_blessing:
            if "回归不等式" in s:
                self.skip = 0

        self.curio = [self.fates[self.fate] + "火漆"] + self.curio
        self.secondary = [self.fates[self.fate]] + self.secondary
