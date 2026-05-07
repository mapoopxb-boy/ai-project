#!/bin/bash
set -e

WORK_DIR="/Users/gongzuo/ai-project/backend"
cd "$WORK_DIR"

# 清理并创建打包目录
rm -rf package && mkdir -p package

# 复制代码文件（排除虚拟环境和缓存）
rsync -av --exclude='myenv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' ./ package/ 2>/dev/null || cp -r . package/

# 安装 Linux 兼容依赖到 package 目录
pip install -r requirements.txt \
    --platform manylinux2014_x86_64 \
    --target package/ \
    --implementation cp \
    --python-version 3.10 \
    --only-binary=:all: \
    --quiet

# 打包
cd package && zip -r ../function.zip . > /dev/null && cd ..
echo "✅ 打包完成，文件大小：$(du -h function.zip | cut -f1)"

# 上传（请确认函数名正确）
tccli scf UpdateFunctionCode \
    --FunctionName AI-agent \
    --ZipFile @./function.zip \
    --Region ap-guangzhou

echo "===== 部署完成 ====="
