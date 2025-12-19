@echo off
chcp 65001 >nul
echo ========================================
echo   Auto Simulated Universe - GUI 启动器
echo ========================================
echo.
echo 提示: 如果想隐藏此窗口,请使用 start_gui.vbs
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python,请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
echo 正在检查依赖...
python -c "import yaml" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 正在安装缺少的依赖...
    pip install -r requirements.txt
)

:: 启动 GUI 服务器
echo.
echo 正在启动 GUI 配置面板...
echo 浏览器将自动打开 http://localhost:8520
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.
python gui_server.py

pause
