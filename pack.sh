#!/bin/bash

# 检查是否在 git 仓库中
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "错误: 当前目录不是 git 仓库"
    exit 1
fi

# 获取仓库根目录的绝对路径
REPO_ROOT=$(git rev-parse --show-toplevel)
# 目标目录在仓库根目录的上一层
TARGET_DIR=$(dirname "$REPO_ROOT")/webui_pack_v1.9

# 创建目标目录
mkdir -p "$TARGET_DIR"
echo "创建目标目录: $TARGET_DIR"

# 获取所有被 git 追踪的文件
FILES=$(git ls-files)

# 复制文件到目标目录
echo "开始复制文件..."
for file in $FILES; do
    # 创建目标文件的目录结构
    target_file="$TARGET_DIR/$file"
    target_dir=$(dirname "$target_file")
    mkdir -p "$target_dir"

    # 复制文件
    cp -p "$file" "$target_file"
done

echo "复制完成！共复制了 $(echo "$FILES" | wc -l | tr -d ' ') 个文件到 $TARGET_DIR"