@echo off
chcp 65001 >nul
title HongHuangHou - 停止服务

echo ========================================
echo  停止所有服务
echo ========================================
echo.

:: 停止 Python 进程 (后端)
echo 停止后端进程...
taskkill /f /im python.exe 2>nul
if errorlevel 1 (
    echo 后端进程未运行
) else (
    echo 后端已停止
)

:: 停止 Node 进程 (前端)
echo 停止前端进程...
taskkill /f /im node.exe 2>nul
if errorlevel 1 (
    echo 前端进程未运行
) else (
    echo 前端已停止
)

echo.
echo 所有服务已停止
echo.
pause