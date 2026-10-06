#!/bin/sh
# 模式: manual(默认, 跑一次退出) | schedule(循环定时执行)
set -e
MODE="${1:-${RUN_MODE:-manual}}"
OUT="${XMR_OUT:-/app/output}"
mkdir -p "$OUT"

if [ "$MODE" = "schedule" ]; then
    INTERVAL="${SCHEDULE_INTERVAL_SECONDS:-86400}"
    echo "[entrypoint] 定时模式: 每 ${INTERVAL}s 执行一次"
    while true; do
        echo "[entrypoint] $(date '+%F %T') 开始执行..."
        python -m xmr.run_all --out "$OUT" || echo "[entrypoint] 本轮执行失败, 等待下轮"
        echo "[entrypoint] $(date '+%F %T') 本轮结束, 休眠 ${INTERVAL}s"
        sleep "$INTERVAL"
    done
else
    exec python -m xmr.run_all --out "$OUT"
fi
