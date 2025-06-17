#!/bin/bash

set -e

sudo true

os="$(uname)"
os_version=$(sw_vers -productVersion)
architecture=$(uname -m)
rosetta_running=$(sysctl -in sysctl.proc_translated)
required_version="13.0"

version_ge() {
    local major1="${1%%.*}"
    local major2="${2%%.*}"
    [[ "$major1" -ge "$major2" ]]
}

if [[ "${os}" == "Darwin" ]]; then
    :
else
    echo "Well, it's for Mac"
    exit 1
fi

if [[ "$rosetta_running" == "1" ]]; then
    echo "The script is running under Rosetta 2. Please close Rosetta 2 to run this script natively on ARM64."
    exit 1
fi

if version_ge "$os_version" $required_version && [[ "$architecture" == "arm64" ]]; then
    :
else
    echo "This script requires macOS Sonoma(13.0) or later and ARM architecture."
    exit 1
fi

if [ -z "${BASH_SOURCE[0]}" ]; then
    echo "Error: BASH_SOURCE is not defined. Make sure you are running this script in a compatible Bash environment."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

cd "$SCRIPT_DIR"

trap 'echo "An error occurred.";exit 1' ERR

if ! xcode-select -p &>/dev/null; then
    echo "安装Xcode Command Line Tools..."
    xcode-select --install

    echo "等待Xcode Command Line Tools安装完成..."
    while true; do
        sleep 20

        if xcode-select -p &>/dev/null; then
            echo "Xcode Command Line Tools已安装完成。"
            break
        else
            echo "正在安装中，请稍候..."
        fi
    done
fi

echo "获取权限"

sudo /usr/bin/xattr -dr com.apple.quarantine "./venv"

echo "创建启动脚本 go-app.command..."

cat <<'EOF' >./go-app.command
#!/bin/bash

if ! xcode-select -p &>/dev/null; then
    echo "安装Xcode Command Line Tools..."
    xcode-select --install
fi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

cd "$SCRIPT_DIR"

WORKDIR=$(pwd)
export PYTHONPATH=WORKDIR
export PATH="$WORKDIR/venv/bin:$PATH"

./venv/bin/python app.py
app_exit_code=$?

if [[ $app_exit_code -ne 0 ]]; then
    echo "应用程序已退出，退出码: $app_exit_code"
    read -p "按回车键退出..."
fi

EOF

chmod +x ./go-app.command

echo "部署完成,点击go-app.command以打开"

rm -- "$0"
