import time

from .predict_system import TextSystem
from .utils import infer_args as init_args
import argparse
import sys


class ONNXPaddleOcr(TextSystem):
    def __init__(self, **kwargs):
        # 默认参数
        parser = init_args()
        inference_args_dict = {}
        for action in parser._actions:
            inference_args_dict[action.dest] = action.default
        params = argparse.Namespace(**inference_args_dict)


        # params.rec_image_shape = "3, 32, 320"
        params.rec_image_shape = "3, 48, 320"

        # 根据传入的参数覆盖更新默认参数
        params.__dict__.update({"cpu": False})
        params.__dict__.update(**kwargs)

        # 初始化模型
        super().__init__(params)

    def ocr(self, img):
        dt_boxes, rec_res = self.__call__(img)
        return [(box.tolist(), res) for box, res in zip(dt_boxes, rec_res)]
