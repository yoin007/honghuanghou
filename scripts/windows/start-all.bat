@echo off
chcp 65001 >nul
title HongHuangHou - 启动全部服务

cd /d %~dp0..\..\

:: 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在，请先运行 install.bat
    pause
    exit /b 1
)

:: 检查前端依赖
if not exist "frontend\node_modules" (
    echo [错误] 前端依赖未安装，请先运行 install.bat
    pause
    exit /b 1
)

echo ========================================
echo  启动后端服务 (新窗口)
echo ========================================
start "HongHuangHou - 后端" cmd /c "%~dp0start-backend.bat"

echo 等待后端启动...
timeout /t 3 /nobreak >nul

echo ========================================
echo  启动前端服务 (新窗口)
echo ========================================
start "HongHuangHou - 前端" cmd /c "%~dp0start-frontend.bat"

echo.
echo ========================================
echo  服务启动完成
echo ========================================
echo.
echo 后端: http://localhost:14600
echo 前端: http://localhost:3333
echo.
echo 关闭此窗口不会停止服务
echo.
pause