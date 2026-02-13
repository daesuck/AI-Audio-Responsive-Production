# v1.0.0 릴리즈 노트

## 포함 기능(요약)
- 오디오 입력(WAV/MP3) 기반 분석 파이프라인
- 모드 판정: SPEECH / MUSIC / IDLE
- 하이라이트/드롭 검출 + 히스테리시스/쿨다운
- Pixel/DMX 시뮬레이터로 데이터 흐름 검증
- Install Wizard(v1): /api/config 기반 설정 저장/조회
- Fail-safe: LAST_HOLD → DIM_AMBIENT(→ DIM_BLACK 옵션) 전이
- 배포 패키징: requirements, scripts, systemd 유닛, 배포 체크리스트

## 실행 방법(개발 환경)
- 테스트 환경 활성화:
  - `python -m venv .venv` (한 번만)
  - `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
- 의존성 설치:
  - `pip install -r requirements.txt`
- 테스트 실행:
  - `pytest`
- Web(UI) 로컬 실행:
  - `uvicorn src.web.app:app --reload --port 8080`
  - 접속: http://127.0.0.1:8080/

## 배포(우분투 서버)
- Git 체크아웃: `git checkout v1.0.0`
- 설치 스크립트 실행:
  - `bash scripts/install.sh`
- systemd 서비스 확인:
  - `systemctl status handds-engine`
  - `systemctl status handds-web`

## 알려진 제한 / 다음 단계
- ESP32 실물 연동(UDP 수신/WS2812 출력)은 다음 단계에서 구현/검증 예정
- Install Wizard는 v1 기준으로 API 중심(간단 UI)
- 하드웨어 송출은 현재 시뮬레이터로 검증, 실제 Art-Net/DMX 송출은 향후 강화 예정

---

작성일: 2026-02-10
