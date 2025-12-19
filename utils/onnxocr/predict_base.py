"""ONNXRuntime 推理 Session 创建封装.

目标:中文 OCR “稳定 + 速度快”.在 Windows + NVIDIA 环境下,
优先使用 `onnxruntime-gpu` 的 CUDAExecutionProvider.

实现原则:
- 只使用 CUDA(不启用 TensorRT/DirectML).
- CUDA 不可用时自动回退 CPU.
- 仅记录一条 OCR 推理模式到日志文件(logs/log.txt).
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import List, Sequence

import onnxruntime

# 项目全局日志:会写入 logs/log.txt
from utils.log import log as _log

class PredictBase(object):
    _windows_dll_dirs_ready: bool = False
    _ocr_mode_logged: bool = False

    def __init__(self, cpu=False):
        self.cpu = cpu

    def get_onnx_session(self, model_dir, use_gpu):
        """创建推理 Session:CUDA 优先,失败回退 CPU."""

        if self.cpu or (use_gpu is False):
            session = self._create_cpu_session(model_dir)
            self._log_ocr_mode_once(session.get_providers())
            return session

        # Windows + Python 3.8+:需要显式 add_dll_directory,否则 ORT CUDA EP 可能报缺少 DLL.
        self._ensure_windows_cuda_dll_dirs()

        available_providers = self._safe_get_available_providers()
        session_options = self._build_session_options()

        cuda_options = {
            "cudnn_conv_algo_search": "HEURISTIC",
            "arena_extend_strategy": "kNextPowerOfTwo",
        }

        requested_cuda = "CUDAExecutionProvider" in available_providers

        if requested_cuda:
            providers = [("CUDAExecutionProvider", cuda_options), "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]

        session = onnxruntime.InferenceSession(
            model_dir, providers=providers, sess_options=session_options
        )

        actual = session.get_providers()
        if requested_cuda and ("CUDAExecutionProvider" not in actual):
            # 保险:避免 CUDA 请求但实际只有 CPU.
            session = self._create_cpu_session(model_dir)
            actual = session.get_providers()

        self._log_ocr_mode_once(actual)
        return session

    def _log_ocr_mode_once(self, providers: Sequence[str]) -> None:
        """把 OCR 模式写入 logs/log.txt(仅一次)."""

        if PredictBase._ocr_mode_logged:
            return

        mode = "CUDA" if "CUDAExecutionProvider" in providers else "CPU"
        try:
            if _log is not None:
                _log.info(f"OCR模式: {mode}")
        finally:
            PredictBase._ocr_mode_logged = True

    def _create_cpu_session(self, model_dir: str):
        session_options = self._build_session_options()
        return onnxruntime.InferenceSession(
            model_dir,
            providers=["CPUExecutionProvider"],
            sess_options=session_options,
        )

    def _safe_get_available_providers(self) -> List[str]:
        try:
            return list(onnxruntime.get_available_providers())
        except Exception:
            return []

    def _ensure_windows_cuda_dll_dirs(self) -> None:
        """把系统 CUDA/cuDNN 的 DLL 目录加入当前进程的 DLL 搜索路径.

        为什么要做:
        - Python 3.8+ 在 Windows 上收紧了 DLL 搜索策略,很多情况下仅改 PATH 不生效.
        - onnxruntime-gpu 的 CUDA EP 会动态加载依赖(cublasLt/cudnn 等),
          若未 add_dll_directory 会报 Error 126(找不到 DLL).
        """

        if os.name != "nt":
            return
        if PredictBase._windows_dll_dirs_ready:
            return

        cuda_roots: List[Path] = []

        # 1) 优先用环境变量(如果存在)
        cuda_path = os.environ.get("CUDA_PATH")
        if cuda_path:
            cuda_roots.append(Path(cuda_path))

        # 2) 常见默认安装路径:遍历 CUDA\v* 目录(支持 12/13 甚至以后)
        default_root = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
        if default_root.exists():
            for child in sorted(default_root.glob("v*"), reverse=True):
                if child.is_dir():
                    cuda_roots.append(child)

        # 去重
        seen: set[str] = set()
        unique_roots: List[Path] = []
        for root in cuda_roots:
            key = str(root).lower()
            if key in seen:
                continue
            seen.add(key)
            unique_roots.append(root)

        dll_dirs: List[Path] = []
        for root in unique_roots:
            # CUDA 13 这次实际 DLL 在 bin\x64 下(你的机器就是这种布局)
            for rel in ("bin\\x64", "bin", "lib\\x64"):
                candidate = root / rel
                if candidate.exists() and candidate.is_dir():
                    dll_dirs.append(candidate)

        # 3) pip 安装的 NVIDIA 运行库(cuDNN/cuBLAS)也可能提供关键 DLL
        # 例如:cudnn64_9.dll 通常位于 site-packages/nvidia/cudnn/bin
        dll_dirs.extend(self._find_pip_nvidia_bin_dirs("nvidia.cudnn"))
        dll_dirs.extend(self._find_pip_nvidia_bin_dirs("nvidia.cublas"))

        # 尝试加入 DLL 搜索路径(不要求全部成功)
        added = 0
        for d in dll_dirs:
            try:
                os.add_dll_directory(str(d))
                added += 1
            except Exception:
                continue

        PredictBase._windows_dll_dirs_ready = True

    def _find_pip_nvidia_bin_dirs(self, module_name: str) -> List[Path]:
        """从 pip 安装的 nvidia.* namespace 包中定位 bin 目录.

        nvidia 的 wheel 多为 namespace 包,没有 __file__,因此用 find_spec.
        """

        try:
            spec = importlib.util.find_spec(module_name)
        except ModuleNotFoundError:
            # nvidia 为 namespace 包:若用户未安装任何 nvidia-* 运行库,会直接抛异常.
            return []
        if not spec or not spec.submodule_search_locations:
            return []

        results: List[Path] = []
        for location in spec.submodule_search_locations:
            base_path = Path(location)
            candidate = base_path / "bin"
            if candidate.exists() and candidate.is_dir():
                results.append(candidate)
        return results

    def _build_session_options(self) -> onnxruntime.SessionOptions:
        session_options = onnxruntime.SessionOptions()
        # ORT_ENABLE_ALL:尽可能做图优化(对大多数 OCR 模型有益)
        session_options.graph_optimization_level = (
            onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        )
        # GPU 推理通常更适合关闭 CPU 内存模式(避免某些动态 shape 场景的开销/碎片)
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
