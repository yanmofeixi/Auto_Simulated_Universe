"""ONNXRuntime 推理 Session 创建封装.

目标:中文 OCR “稳定 + 速度快”.

实现原则:
- 仅使用 CPU 推理.
- 仅记录一条 OCR 推理模式到日志文件(logs/log.txt).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Sequence

import onnxruntime

# 项目全局日志:会写入 logs/log.txt
from utils.log import log as _log

class PredictBase(object):
    _ocr_mode_logged: bool = False

    def __init__(self, cpu=True):
        self.cpu = cpu

    def get_onnx_session(self, model_dir):
        """创建推理 Session: 仅支持 CPU."""
        session = self._create_cpu_session(model_dir)
        self._log_ocr_mode_once(session.get_providers())
        return session

    def _log_ocr_mode_once(self, providers: Sequence[str]) -> None:
        """把 OCR 模式写入 logs/log.txt(仅一次)."""

        if PredictBase._ocr_mode_logged:
            return

        try:
            if _log is not None:
                _log.info("OCR模式: CPU")
        finally:
            PredictBase._ocr_mode_logged = True

    def _create_cpu_session(self, model_dir: str):
        session_options = self._build_session_options()
        return onnxruntime.InferenceSession(
            model_dir,
            providers=["CPUExecutionProvider"],
            sess_options=session_options,
        )

    def _build_session_options(self) -> onnxruntime.SessionOptions:
        session_options = onnxruntime.SessionOptions()
        # 尽可能做图优化(对大多数 OCR 模型有益)
        session_options.graph_optimization_level = (
            onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        session_options.enable_mem_pattern = False
        session_options.enable_cpu_mem_arena = True
        return session_options


    def get_output_name(self, onnx_session):
        """
        output_name = onnx_session.get_outputs()[0].name
        :param onnx_session:
        :return:
        """
        output_name = []
        for node in onnx_session.get_outputs():
            output_name.append(node.name)
        return output_name

    def get_input_name(self, onnx_session):
        """
        input_name = onnx_session.get_inputs()[0].name
        :param onnx_session:
        :return:
        """
        input_name = []
        for node in onnx_session.get_inputs():
            input_name.append(node.name)
        return input_name

    def get_input_feed(self, input_name, image_numpy):
        """
        input_feed={self.input_name: image_numpy}
        :param input_name:
        :param image_numpy:
        :return:
        """
        input_feed = {}
        for name in input_name:
            input_feed[name] = image_numpy
        return input_feed
