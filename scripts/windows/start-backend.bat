@echo off
chcp 65001 >nul
title HongHuangHou - 启动后端

cd /d %~dp0..\..\

:: 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [错误] 虚拟环境不存在，请先运行 install.bat
    pause
    exit /b 1
)

:: 进入后端目录
cd lesson

:: 设置环境变量
set CORS_ORIGINS=http://localhost:3333,https://localhost:3333
set FORCE_HTTPS=false

echo ========================================
echo  启动后端服务 (端口 14600)
echo ========================================
echo.

:: 启动服务
python main.py

pause