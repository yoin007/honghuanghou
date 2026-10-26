@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM 增量部署脚本（先备份、再部署）- 在服务器解压目录中运行
REM 用法: deploy.bat [项目根目录]
REM       或直接运行后按提示输入项目根目录
REM 注意: 本文件为 ANSI/GBK 编码，请勿另存为 UTF-8
REM ============================================================

if "%~1"=="" (
    set /p "PROJECT_ROOT=请输入服务器项目根目录（例如 D:\projects\honghuanghou）: "
) else (
    set "PROJECT_ROOT=%~1"
)

REM 去掉结尾反斜杠和引号
set "PROJECT_ROOT=!PROJECT_ROOT:"=!"
if "!PROJECT_ROOT:~-1!"=="\" set "PROJECT_ROOT=!PROJECT_ROOT:~0,-1!"

if not exist "%PROJECT_ROOT%\" (
    echo [错误] 项目根目录不存在: %PROJECT_ROOT%
    pause
    exit /b 1
)

if not exist "%~dp0filelist.txt" (
    echo [错误] 未找到 filelist.txt，请在 ZIP 解压后的 _deploy 目录中运行本脚本
    pause
    exit /b 1
)

REM 包根 = 本脚本所在 _deploy 目录的上一级（业务文件 lesson/frontend 与 _deploy 同级）
for %%I in ("%~dp0..") do set "PKG_ROOT=%%~fI"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "BACKUP_DIR=%~dp0backup_%TS%"
set "FAIL=0"

echo ============================================================
echo [1/3] 备份将被覆盖的现有文件...
echo     备份目录: %BACKUP_DIR%
echo ------------------------------------------------------------

set /a COUNT=0
for /f "usebackq delims=" %%L in (`type "%~dp0filelist.txt"`) do (
    set "REL=%%L"
    set "REL=!REL:/=\!"
    if exist "%PROJECT_ROOT%\!REL!" (
        call :copy_one "%PROJECT_ROOT%\!REL!" "%BACKUP_DIR%\!REL!"
        if !COPY_OK! equ 1 (
            echo   [已备份] !REL!
            set /a COUNT+=1
        ) else (
            echo   [备份失败] !REL!
            set "FAIL=1"
        )
    ) else (
        echo   [新文件，无需备份] !REL!
    )
)

if "!FAIL!"=="1" (
    echo [错误] 存在备份失败的文件，已中止部署。请检查磁盘权限后重试。
    pause
    exit /b 1
)

copy /y "%~dp0filelist.txt" "%BACKUP_DIR%\filelist.txt" >nul
copy /y "%~dp0restore.bat" "%BACKUP_DIR%\restore.bat" >nul
echo     共备份 !COUNT! 个旧文件（含 restore.bat，可用于一键回滚）

echo ============================================================
echo [2/3] 准备部署新文件...
echo ------------------------------------------------------------

set /a DCOUNT=0
for /f "usebackq delims=" %%L in (`type "%~dp0filelist.txt"`) do (
    set "REL=%%L"
    set "REL=!REL:/=\!"
    if exist "%PKG_ROOT%\!REL!" (
        echo   [待部署] !REL!
        set /a DCOUNT+=1
    ) else (
        echo   [错误] 包中缺少文件: !REL!
        echo          （请检查 ZIP 是否完整解压：_deploy 应与 lesson/frontend 同级）
        set "FAIL=1"
    )
)

if "!FAIL!"=="1" (
    echo [错误] 部署包不完整，已中止。旧文件备份仍在 %BACKUP_DIR%
    pause
    exit /b 1
)

echo.
set /p "CONFIRM=确认部署以上 !DCOUNT! 个文件？此操作会覆盖服务器现有文件 (y/n): "
if /i not "!CONFIRM!"=="y" (
    echo 已取消部署。旧文件备份仍在 %BACKUP_DIR%
    pause
    exit /b 0
)

echo ============================================================
echo [3/3] 覆盖部署...
echo ------------------------------------------------------------

for /f "usebackq delims=" %%L in (`type "%~dp0filelist.txt"`) do (
    set "REL=%%L"
    set "REL=!REL:/=\!"
    call :copy_one "%PKG_ROOT%\!REL!" "%PROJECT_ROOT%\!REL!"
    if !COPY_OK! equ 1 (
        echo   [已部署] !REL!
    ) else (
        echo   [部署失败] !REL!
        set "FAIL=1"
    )
)

if "!FAIL!"=="1" (
    echo.
    echo [错误] 存在部署失败的文件！系统可能处于不一致状态。
    echo 立即回滚: restore.bat "%BACKUP_DIR%" "%PROJECT_ROOT%"
    pause
    exit /b 1
)

echo ============================================================
echo 部署完成！本次共部署 !DCOUNT! 个文件。
echo.
echo 后续步骤:
echo   1. 重启后端服务（python main.py）
echo   2. 前端浏览器强刷（Ctrl+Shift+R）
echo   3. 数据库表/权限配置在启动时自动迁移
echo.
echo 如需回滚:
echo   restore.bat "%BACKUP_DIR%" "%PROJECT_ROOT%"
echo ============================================================
pause
exit /b 0

REM ------------------------------------------------------------
REM 子程序：复制单个文件，自动创建目标目录
REM 参数: %~1 源文件完整路径  %~2 目标文件完整路径
REM 结果: COPY_OK=1 成功 / 0 失败
REM ------------------------------------------------------------
:copy_one
set "CP_SRC=%~f1"
set "CP_DST=%~f2"
set "COPY_OK=0"
if not exist "%CP_SRC%" goto :eof
for %%S in ("%CP_SRC%") do set "CP_SDIR=%%~dpS"
for %%D in ("%CP_DST%") do set "CP_DDIR=%%~dpD"
if "!CP_SDIR:~-1!"=="\" set "CP_SDIR=!CP_SDIR:~0,-1!"
if "!CP_DDIR:~-1!"=="\" set "CP_DDIR=!CP_DDIR:~0,-1!"
if not exist "!CP_DDIR!\" mkdir "!CP_DDIR!"
echo     [执行] copy /y "!CP_SRC!" "!CP_DST!"
copy /y "!CP_SRC!" "!CP_DST!"
if errorlevel 1 (
    echo     [复制命令失败] errorlevel=!errorlevel! 源:!CP_SRC!
    goto :eof
)
REM 实测校验：源与目标文件大小一致才算复制成功
for %%A in ("!CP_SRC!") do set "CP_SZ1=%%~zA"
for %%B in ("!CP_DST!") do set "CP_SZ2=%%~zB"
echo     [复制] !CP_SZ1! -> !CP_SZ2! 字节: !CP_DST!
if "!CP_SZ1!"=="!CP_SZ2!" set "COPY_OK=1"
goto :eof
