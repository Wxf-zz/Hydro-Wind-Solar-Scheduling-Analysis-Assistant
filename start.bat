@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo 未找到 Python。请安装 Python 3.12 后重新运行。
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo 正在创建 Python 虚拟环境...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
)

echo 正在检查并安装依赖...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo 正在启动水风光调度智能分析助手...
".venv\Scripts\python.exe" -m streamlit run app.py
exit /b %errorlevel%

:error
echo 启动失败，请根据上面的提示检查 Python、网络或依赖安装情况。
pause
exit /b 1
