import cv2 as cv
import numpy as np
from utils.common.ocr_utils import (
    fuzzy_match,
    is_edit_distance_at_most_one as _is_edit_distance_at_most_one,
)
from utils.log import log
from utils.ocr_defaults import (
    BLESSINGS_BY_FATE,
    DEFAULT_CURIO,
    DEFAULT_PRIOR_BLESSING,
    DEFAULT_SECONDARY_FATES,
    FATES,
)
from utils.onnxocr.onnx_paddleocr import ONNXPaddleOcr

# mode: blessing1 blessing2 curio


class My_TS:
    def __init__(self, lang="ch"):
        self.lang = lang
        self.ts = ONNXPaddleOcr(use_angle_cls=False)
        self.text = ""

    def is_edit_distance_at_most_one(self, str1, str2, ch):
        """检查两个字符串的编辑距离是否不超过1."""
        return _is_edit_distance_at_most_one(str1, str2, ch)

    def sim(self, text, img=None):
        if img is not None:
            self.input(img)
        return fuzzy_match(text, self.text)

    def ocr_one_row(self, img):
        return self.ts.text_recognizer([img])[0][0]

    def input(self, img):
        try:
            self.text = self.ocr_one_row(img).lower()
        except:
            self.text = ""

    def sim_list(self, text_list, img=None):
        if img is not None:
            self.input(img)
        for t in text_list:
            if self.sim(t):
                return t
        return None

    def split_and_find(self, key_list, img, mode=None, blessing_skip=1):
        white = [255, 255, 255]
        yellow = [126, 162, 180]
        binary_image = np.zeros_like(img[:, :, 0])
        enhance_image = np.zeros_like(img)
        if mode == "curio":
            binary_image[np.sum((img - yellow) ** 2, axis=-1) <= 512] = 255
            enhance_image[np.sum((img - yellow) ** 2, axis=-1) <= 3200] = [
                255,
                255,
                255,
            ]
        else:
            binary_image[np.sum((img - white) ** 2, axis=-1) <= 1600] = 255
            enhance_image[np.sum((img - white) ** 2, axis=-1) <= 3200] = [255, 255, 255]
        if mode == "blessing":
            kerneld = np.zeros((7, 3), np.uint8) + 1
            kernele = np.zeros((1, 39), np.uint8) + 1
            kernele2 = np.zeros((7, 1), np.uint8) + 1
            binary_image = cv.dilate(binary_image, kerneld, iterations=2)
            binary_image = cv.erode(binary_image, kernele, iterations=5)
            binary_image = cv.erode(binary_image, kernele2, iterations=2)
            enhance_image = img
        else:
            kernel = np.zeros((5, 9), np.uint8) + 1
            for i in range(2):
                binary_image = cv.dilate(binary_image, kernel, iterations=3)
                binary_image = cv.erode(binary_image, kernel, iterations=2)
        contours, _ = cv.findContours(
            binary_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE
        )
        prior = len(key_list)
        rcx, rcy, find, black = -1, -1, 0, 0
        res = ""
        text_res = "."
        for c, contour in enumerate(contours):
            x, y, w, h = cv.boundingRect(contour)
            if h == binary_image.shape[0] or w < 55:
                continue
            roi = enhance_image[y : y + h, x : x + w]
            cx = x + w // 2
            cy = y + h // 2
            self.input(roi)
            if len(self.text.strip()) <= 1:
                continue
            if find == 0:
                rcx, rcy, find, text_res = cx, cy, 1, self.text + ";"
            res += "|" + self.text
            if (self.sim("回归不等式") and blessing_skip) or self.sim_list(
                ["银河大乐透", "普通八卦", "愚者面具", "机械齿轮"]
            ) is not None:
                black = 1
                res += "x"
                continue
            if find == 1:
                rcx, rcy, text_res = cx, cy, self.text + "?"
            for i, text in enumerate(key_list):
                if i == prior:
                    break
                if self.sim(text):
                    rcx, rcy, find = cx, cy, 2
                    text_res = text + "!"
                    prior = i
        print("识别结果:", res + "|", " 识别到:", text_res)
        if black and find == 1:
            find = 3
        return (rcx - img.shape[1] // 2, rcy - img.shape[0] // 2), find + black

    def find_text(self, img, text, env=None):
        self.nothing = 1
        results = self.ts.ocr(img)
        for txt in text:
            for res in results:
                res = {
                    "raw_text": res[1][0],
                    "box": np.array(res[0]),
                    "score": res[1][1],
                }
                self.text = res["raw_text"]
                if len(self.text.strip()) > 1 and "UID" not in self.text:
                    self.nothing = 0
                if self.sim(txt):
                    print("识别到文本:", txt, "匹配文本:", self.text)
                    return res["box"]
        return None


class text_keys:
    def __init__(self, fate=4):
        self.fate = fate
        self.interacts = [
            "黑塔",
            "区域",
            "事件",
            "退出",
            "沉浸",
            "紧锁",
            "复活",
            "下载",
            "模拟",
        ]
        self.fates = list(FATES)
        self.prior_blessing = list(DEFAULT_PRIOR_BLESSING)
        self.curio = list(DEFAULT_CURIO)
        self.blessings = [list(items) for items in BLESSINGS_BY_FATE]
        self.secondary = list(DEFAULT_SECONDARY_FATES)
        try:
            import yaml

            with open("info.yml", "r", encoding="utf-8", errors="ignore") as f:
                config = yaml.safe_load(f)["prior"]
            with open("info.yml", "r", encoding="utf-8", errors="ignore") as f:
                try:
                    self.secondary = yaml.safe_load(f)["config"]["secondary_fate"]
                except:
                    pass
            for i, j in enumerate(config):
                if i > 1:
                    self.blessings[i - 2] = config[j]
                elif i == 0:
                    self.curio = config[j]
        except:
            pass
        self.prior_blessing += self.blessings[fate]
        self.skip = 1
        for s in self.prior_blessing:
            if "回归不等式" in s:
                self.skip = 0
        self.curio = [self.fates[self.fate] + "火漆"] + self.curio
        self.secondary = [self.fates[self.fate]] + self.secondary
