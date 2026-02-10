#!/bin/bash
# 웹서버(FastAPI + uvicorn) 실행 스크립트

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PATH="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/web.log"

# 로그 디렉터리 생성
mkdir -p "$LOG_DIR"

# venv 활성화
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "경고: venv를 찾을 수 없습니다. ($VENV_PATH)"
    echo "설치 스크립트를 먼저 실행하세요: $SCRIPT_DIR/install.sh"
    exit 1
fi

cd "$PROJECT_ROOT"

# 웹서버 포트 설정 (기본 8000, 환경변수로 오버라이드 가능)
WEB_PORT="${WEB_PORT:-8000}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"

echo "[$(date)] 웹서버 시작..." >> "$LOG_FILE"
uvicorn src.web.app:app --host "$WEB_HOST" --port "$WEB_PORT" >> "$LOG_FILE" 2>&1 &

echo "웹서버 PID: $!"
echo "$!" > "$LOG_DIR/web.pid"
