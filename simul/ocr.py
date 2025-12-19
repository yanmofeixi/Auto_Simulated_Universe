import cv2 as cv
import numpy as np
from utils.common.ocr_utils import (
    fuzzy_match,
    is_edit_distance_at_most_one as _is_edit_distance_at_most_one,
)
from utils.log import log
from utils.onnxocr.onnx_paddleocr import ONNXPaddleOcr
from simul.config import config as simul_config

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
        # 从 config 获取祝福黑名单
        blessing_blacklist = simul_config.get_blessing_blacklist()
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
            # 检查是否在黑名单中
            if (self.sim("回归不等式") and blessing_skip) or self.sim_list(
                blessing_blacklist[1:]  # 跳过 "回归不等式"
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
        # 从 config 加载所有词表
        self.interacts = simul_config.get_interacts("simul")
        self.fates = simul_config.get_fates()
        self.prior_blessing = simul_config.get_prior_blessing()
        self.curio = simul_config.get_curio()
        self.blessings = simul_config.get_blessings_by_fate()
        self.secondary = simul_config.get_secondary_fates()

        # 从 config 读取用户配置,覆盖默认值
        data = simul_config.load_yaml()
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
