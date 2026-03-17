@echo off
chcp 65001 >nul
title HongHuangHou - 启动前端

cd /d %~dp0..\..\frontend

:: 检查 node_modules
if not exist "node_modules" (
    echo [错误] node_modules 不存在，请先运行 install.bat
    pause
    exit /b 1
)

echo ========================================
echo  启动前端开发服务 (端口 3333)
echo ========================================
echo.

:: 启动前端
call npm run dev

pause