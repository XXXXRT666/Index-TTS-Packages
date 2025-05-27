@echo off
setlocal enabledelayedexpansion

REM 将工作目录切换到脚本所在的目录
cd /d "%~dp0"
echo 已切换到脚本所在目录: %cd%

REM 检测操作系统
echo 检测到操作系统: Windows

REM 检查是否安装了Chocolatey
echo 检查是否安装了Chocolatey...
where choco >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Chocolatey未安装，准备安装...
    @powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"

    where choco >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo 安装Chocolatey失败，请手动安装: https://chocolatey.org/install
        pause
        exit /b 1
    )
    echo Chocolatey安装完成

    REM 配置Chocolatey使用中国镜像源
    choco source add -n=tsinghua -s=https://mirrors.tuna.tsinghua.edu.cn/chocolatey/ --priority=1
) else (
    echo 检测到Chocolatey已安装
)

REM 检查是否安装了ffmpeg
echo 检查是否安装了ffmpeg...
where ffmpeg >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ffmpeg未安装，准备安装...
    choco install ffmpeg -y
    if %ERRORLEVEL% neq 0 (
        echo 安装ffmpeg失败
        pause
        exit /b 1
    )
    echo ffmpeg安装完成
    REM 刷新环境变量
    refreshenv
) else (
    echo 检测到ffmpeg已安装
)

REM 初始化Python命令变量
set "PYTHON_CMD="
set "PYTHON310_CMD="

REM 检查是否有Python 3.10
python --version 2>nul | findstr /C:"Python 3.10" >nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=python"
    set "PYTHON310_CMD=python"
    echo 找到Python 3.10
) else (
    py -3.10 --version 2>nul | findstr /C:"Python 3.10" >nul
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_CMD=py -3.10"
        set "PYTHON310_CMD=py -3.10"
        echo 找到Python 3.10
    ) else (
        REM 检查其他Python版本
        where python >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            set "PYTHON_CMD=python"
        ) else (
            where py >nul 2>nul
            if %ERRORLEVEL% equ 0 (
                set "PYTHON_CMD=py"
            )
        )
    )
)

REM 如果找到了Python，检查版本
set "NEED_INSTALL=true"
if defined PYTHON_CMD (
    for /f "tokens=*" %%i in ('!PYTHON_CMD! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
        set "PYTHON_VERSION=%%i"
    )

    if not "!PYTHON_VERSION!"=="" (
        echo 检测到Python版本为 !PYTHON_VERSION!

        REM 比较版本号
        for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
            set "MAJOR=%%a"
            set "MINOR=%%b"
        )

        if !MAJOR! equ 3 (
            if !MINOR! equ 10 (
                set "NEED_INSTALL=false"
                echo Python版本正是所需的3.10版本
            ) else (
                echo Python版本不是3.10，需要安装Python 3.10
            )
        ) else (
            echo Python版本不是3.10，需要安装Python 3.10
        )
    ) else (
        echo 无法获取Python版本
    )
) else (
    echo 未检测到Python，需要安装Python 3.10
)

REM 安装Python 3.10（如果需要）
if "!NEED_INSTALL!"=="true" (
    echo 准备安装Python 3.10...

    echo 使用Chocolatey安装Python 3.10...
    choco install python310 -y
    if %ERRORLEVEL% neq 0 (
        echo 安装Python 3.10失败
        echo 请从 https://npm.taobao.org/mirrors/python/3.10.0/ 手动下载安装Python 3.10
        pause
        exit /b 1
    )

    REM 刷新环境变量
    refreshenv
    set "PYTHON_CMD=python"
    echo Python 3.10安装完成
)

REM 再次验证Python版本
for /f "tokens=*" %%i in ('!PYTHON_CMD! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
    set "PYTHON_VERSION=%%i"
)

echo 使用Python版本: !PYTHON_VERSION!

REM 确认是否为3.10版本
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set "MAJOR=%%a"
    set "MINOR=%%b"
)

if not !MAJOR! equ 3 (
    echo 错误: Python主版本号必须为3，当前为!MAJOR!
    pause
    exit /b 1
)

if not !MINOR! equ 10 (
    echo 错误: Python次版本号必须为10，当前为!MINOR!
    pause
    exit /b 1
)

REM 如果版本检查通过，继续执行后续操作
echo 开始执行主程序...

REM 创建虚拟环境
echo 正在创建虚拟环境...
!PYTHON_CMD! -m venv venv
if %ERRORLEVEL% neq 0 (
    echo 错误: 创建虚拟环境失败
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo 错误: 激活虚拟环境失败
    pause
    exit /b 1
)

REM 配置pip使用中国大陆镜像源
echo 配置pip使用中国大陆镜像源...
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

REM 安装依赖
echo 正在安装依赖...
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo 错误: 安装依赖失败
    pause
    exit /b 1
)

REM 运行应用程序
echo 正在启动应用程序...
where python
python app.py
set APP_EXIT_CODE=%ERRORLEVEL%

if %APP_EXIT_CODE% neq 0 (
    echo 应用程序已退出，退出码: %APP_EXIT_CODE%
    pause
)

endlocal
