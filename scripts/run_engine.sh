#!/bin/bash
# 엔진 실행 스크립트 (systemd 또는 수동 실행 용)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PATH="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/engine.log"

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

# 엔진 실행 (main.py 실시간 루프 사용)
cd "$PROJECT_ROOT"
echo "[$(date)] 엔진 시작..." >> "$LOG_FILE"
python -m src.engine.main >> "$LOG_FILE" 2>&1 &

echo "엔진 PID: $!"
echo "$!" > "$LOG_DIR/engine.pid"
