%1 mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/c %~s0 ::","","runas",1)(window.close)&&exit
@echo off
chcp 65001 >nul

cd /d "%~dp0"

REM 说明:
REM - 不强制 Python 版本:使用当前系统的 `py`/`python` 环境.
REM - 依赖安装需要额外源:
REM   1) NVIDIA PyPI(CUDA/cuDNN/cuBLAS) https://pypi.nvidia.com
REM   2) onnxruntime CUDA13 nightly(Python3.13 的 onnxruntime-gpu)
REM      https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-13-nightly/pypi/simple/

py -m pip install -U pip
py -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --upgrade --pre --extra-index-url https://pypi.nvidia.com --extra-index-url https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-13-nightly/pypi/simple/

pause
