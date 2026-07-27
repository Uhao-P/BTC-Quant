#!/usr/bin/env bash
# BTC-Quant 初始化
set -e

cd "$(dirname "$0")/.."

echo "=== BTC-Quant 初始化 ==="

# Python venv
if [ ! -d "venv" ]; then
    echo "[1/3] 创建 Python venv..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "[2/3] 安装 Python 依赖..."
pip install -r requirements.txt -q

# Frontend
echo "[3/3] 安装前端依赖..."
cd frontend
pnpm install
cd ..

echo ""
echo "=== 初始化完成 ==="
echo ""
echo "启动方式:"
echo "  后台采集: python scripts/collector_daemon.py"
echo "  历史回填: python scripts/backfill.py --timeframe 1h --bars 1000"
echo "  API 服务: uvicorn backend.main:app --host 127.0.0.1 --port 8700 --reload"
echo "  前端:    cd frontend && pnpm dev"
