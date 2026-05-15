#!/bin/bash
# AutoSeller 서버 시작 (기존 프로세스 종료 후 재시작)

PORT=5001
ROOT="$(cd "$(dirname "$0")" && pwd)"

# 기존 프로세스 종료
PIDS=$(lsof -ti tcp:$PORT 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "기존 서버 종료 (PID: $PIDS)"
    kill $PIDS
    sleep 1
fi

echo "AutoSeller 서버 시작 → http://localhost:$PORT"
cd "$ROOT"
python3 web/app.py
