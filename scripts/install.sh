#!/bin/bash
# AI Stage Lighting System 설치 스크립트
# Ubuntu 20.04+ 대상

set -e

echo "=== AI Stage Lighting System 설치 시작 ==="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# 시스템 의존성 확인 및 설치
echo "[1/4] 시스템 의존성 확인/설치..."
if ! command -v python3 &> /dev/null; then
    echo "python3 설치 중..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
fi

if ! command -v pip3 &> /dev/null; then
    sudo apt-get install -y python3-pip
fi

# ffmpeg 확인/설치 (MP3 지원)
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg 설치 중..."
    sudo apt-get install -y ffmpeg
fi

# venv 생성 (없으면)
echo "[2/4] Python venv 설정..."
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    python3 -m venv "$PROJECT_ROOT/venv"
    echo "venv 생성 완료"
fi

# venv 활성화 후 pip 업그레이드/의존성 설치
source "$PROJECT_ROOT/venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "$PROJECT_ROOT/requirements.txt"
echo "Python 의존성 설치 완료"

# systemd 서비스 파일 복사/활성화
echo "[3/4] systemd 서비스 설정..."
if [ -f "$PROJECT_ROOT/systemd/handds-engine.service" ]; then
    sudo cp "$PROJECT_ROOT/systemd/handds-engine.service" /etc/systemd/system/
    echo "handds-engine.service 설치됨"
fi
if [ -f "$PROJECT_ROOT/systemd/handds-web.service" ]; then
    sudo cp "$PROJECT_ROOT/systemd/handds-web.service" /etc/systemd/system/
    echo "handds-web.service 설치됨"
fi

if [ -f /etc/systemd/system/handds-engine.service ] || [ -f /etc/systemd/system/handds-web.service ]; then
    sudo systemctl daemon-reload
    sudo systemctl enable handds-engine.service 2>/dev/null || true
    sudo systemctl enable handds-web.service 2>/dev/null || true
    echo "systemd 활성화 완료"
fi

# 로그 디렉터리 생성
echo "[4/4] 로그 디렉터리 생성..."
mkdir -p "$PROJECT_ROOT/logs"

# 실행 권한 설정
chmod +x "$PROJECT_ROOT/scripts/run_engine.sh"
chmod +x "$PROJECT_ROOT/scripts/run_web.sh"

echo ""
echo "=== 설치 완료 ==="
echo ""
echo "다음 단계:"
echo ""
echo "1) 엔진 시작:"
echo "   systemctl start handds-engine  # systemd 사용 시"
echo "   # 또는 수동:"
echo "   bash $SCRIPT_DIR/run_engine.sh"
echo ""
echo "2) 웹서버(Install Wizard) 시작:"
echo "   systemctl start handds-web  # systemd 사용 시"
echo "   # 또는 수동:"
echo "   bash $SCRIPT_DIR/run_web.sh"
echo ""
echo "3) 상태 확인:"
echo "   systemctl status handds-engine"
echo "   systemctl status handds-web"
echo ""
echo "4) 로그 보기:"
echo "   tail -f $PROJECT_ROOT/logs/engine.log"
echo "   tail -f $PROJECT_ROOT/logs/web.log"
echo ""
