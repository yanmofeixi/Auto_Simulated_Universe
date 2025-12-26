%1 mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/c %~s0 ::","","runas",1)(window.close)&&exit
@echo off
chcp 65001 >nul

cd /d "%~dp0"

REM 说明:
REM - 不强制 Python 版本:使用当前系统的 `py`/`python` 环境.

py -m pip install -U pip
py -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --upgrade

pause
