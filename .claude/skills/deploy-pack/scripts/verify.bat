@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM 部署校验脚本 - 核对项目中的文件与部署包是否一致（按字节大小）
REM 用法: verify.bat [项目根目录]  （在解压目录的 _deploy 中运行）
REM ============================================================

if "%~1"=="" (
    set /p "PROJECT_ROOT=请输入服务器项目根目录: "
) else (
    set "PROJECT_ROOT=%~1"
)

set "PROJECT_ROOT=!PROJECT_ROOT:"=!"
if "!PROJECT_ROOT:~-1!"=="\" set "PROJECT_ROOT=!PROJECT_ROOT:~0,-1!"

for %%I in ("%~dp0..") do set "PKG_ROOT=%%~fI"

if not exist "%~dp0filelist.txt" (
    echo [错误] 未找到 filelist.txt
    pause
    exit /b 1
)

echo ============================================================
echo 核对部署结果（包内文件 vs 项目文件，按字节大小）
echo     包根: %PKG_ROOT%
echo     项目: %PROJECT_ROOT%
echo ------------------------------------------------------------

set /a OK=0
set /a BAD=0
for /f "usebackq delims=" %%L in (`type "%~dp0filelist.txt"`) do (
    set "REL=%%L"
    set "REL=!REL:/=\!"
    set "PKG_FILE=%PKG_ROOT%\!REL!"
    set "PRJ_FILE=%PROJECT_ROOT%\!REL!"
    if not exist "!PKG_FILE!" (
        echo   [异常] 包内缺失: !REL!
        set /a BAD+=1
    ) else if not exist "!PRJ_FILE!" (
        echo   [缺失] 项目中不存在: !REL!
        set /a BAD+=1
    ) else (
        for %%A in ("!PKG_FILE!") do set "SZ1=%%~zA"
        for %%B in ("!PRJ_FILE!") do set "SZ2=%%~zB"
        for %%C in ("!PKG_FILE!") do set "MT1=%%~tC"
        for %%D in ("!PRJ_FILE!") do set "MT2=%%~tD"
        if "!SZ1!"=="!SZ2!" (
            echo   [一致] !REL!  !SZ2! 字节  项目时间: !MT2!
            set /a OK+=1
        ) else (
            echo   [不一致] !REL!  包内 !SZ1! 字节 vs 项目 !SZ2! 字节
            set /a BAD+=1
        )
    )
)

echo ------------------------------------------------------------
echo 校验完成: !OK! 个一致, !BAD! 个不一致/缺失
if !BAD! gtr 0 (
    echo 存在未正确部署的文件！请确认 PROJECT_ROOT 是否为实际运行的项目目录。
) else (
    echo 全部一致。若页面仍显示旧功能，请重启 vite 前端服务并强刷浏览器。
)
echo ============================================================
pause
