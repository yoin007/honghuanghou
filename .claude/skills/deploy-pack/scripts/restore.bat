@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM 回滚脚本 - 把备份目录中的旧文件恢复回项目
REM 用法: restore.bat [备份目录] [项目根目录]
REM       备份目录即 deploy.bat 运行时生成的 backup_时间戳 目录
REM 注意: 本文件为 ANSI/GBK 编码，请勿另存为 UTF-8
REM ============================================================

if "%~1"=="" (
    set /p "BACKUP_DIR=请输入备份目录路径（backup_时间戳 目录）: "
) else (
    set "BACKUP_DIR=%~1"
)

if "%~2"=="" (
    set /p "PROJECT_ROOT=请输入服务器项目根目录: "
) else (
    set "PROJECT_ROOT=%~2"
)

set "BACKUP_DIR=!BACKUP_DIR:"=!"
set "PROJECT_ROOT=!PROJECT_ROOT:"=!"
if "!BACKUP_DIR:~-1!"=="\" set "BACKUP_DIR=!BACKUP_DIR:~0,-1!"
if "!PROJECT_ROOT:~-1!"=="\" set "PROJECT_ROOT=!PROJECT_ROOT:~0,-1!"

if not exist "%BACKUP_DIR%\filelist.txt" (
    echo [错误] 备份目录无效（未找到 filelist.txt）: %BACKUP_DIR%
    pause
    exit /b 1
)
if not exist "%PROJECT_ROOT%\" (
    echo [错误] 项目根目录不存在: %PROJECT_ROOT%
    pause
    exit /b 1
)

echo ============================================================
echo 即将把以下文件从备份恢复到项目（覆盖现有新文件）:
echo     备份来源: %BACKUP_DIR%
echo     恢复目标: %PROJECT_ROOT%
echo ------------------------------------------------------------
for /f "usebackq delims=" %%L in (`type "%BACKUP_DIR%\filelist.txt"`) do (
    set "REL=%%L"
    set "REL=!REL:/=\!"
    if exist "%BACKUP_DIR%\!REL!" (
        echo   [待恢复] !REL!
    ) else (
        echo   [备份中不存在，跳过] !REL!
    )
)
echo ------------------------------------------------------------
set /p "CONFIRM=确认回滚 (y/n): "
if /i not "!CONFIRM!"=="y" (
    echo 已取消。
    pause
    exit /b 0
)

set /a COUNT=0
set "FAIL=0"
for /f "usebackq delims=" %%L in (`type "%BACKUP_DIR%\filelist.txt"`) do (
    set "REL=%%L"
    set "REL=!REL:/=\!"
    if exist "%BACKUP_DIR%\!REL!" (
        call :copy_one "%BACKUP_DIR%\!REL!" "%PROJECT_ROOT%\!REL!"
        if !COPY_OK! equ 1 (
            echo   [已恢复] !REL!
            set /a COUNT+=1
        ) else (
            echo   [恢复失败] !REL!
            set "FAIL=1"
        )
    )
)

if "!FAIL!"=="1" (
    echo [错误] 存在恢复失败的文件，请手工检查 %BACKUP_DIR%
    pause
    exit /b 1
)

echo ============================================================
echo 回滚完成！共恢复 !COUNT! 个文件。
echo 请重启后端服务并强刷浏览器。
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
