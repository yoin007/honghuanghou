@echo off
chcp 65001 >nul
title HongHuangHou - 安装依赖

cd /d %~dp0..\..\

echo ========================================
echo  HongHuangHou 项目依赖安装
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [警告] 未找到 Node.js，前端将无法运行
    echo        如需运行前端，请安装 Node.js 18+
)

echo [1/4] 创建 Python 虚拟环境...
if not exist "venv" (
    python -m venv venv
    echo 虚拟环境创建成功
) else (
    echo 虚拟环境已存在
)

echo.
echo [2/4] 安装后端依赖...
call venv\Scripts\activate
pip install -r lesson\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)

echo.
echo [3/4] 初始化数据库...
cd lesson
python scripts\init_databases.py
cd ..

echo.
echo [4/4] 安装前端依赖...
if exist "frontend\package.json" (
    cd frontend
    call npm install
    cd ..
) else (
    echo 前端目录不存在，跳过
)

echo.
echo ========================================
echo  安装完成！
echo ========================================
echo.
echo 下一步：
echo  1. 修改 lesson\config\lesson.yaml 中的 Windows 路径
echo  2. 运行 start-all.bat 启动项目
echo.
pause