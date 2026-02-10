# 배포 체크리스트

AI Stage Lighting System 릴리스 및 배포 절차

## 프리-릴리스 확인 (개발 환경)

- [ ] 최신 코드 커밋 완료
- [ ] `git status` 확인 (uncommitted 변경사항 없음)
- [ ] 로컬 환경에서 테스트 실행:
  ```bash
  cd d:/Codex/AI_Stage_Lighting_System
  python -m pytest -v
  ```
  - 최소 모든 테스트 PASS 필수
- [ ] 주요 기능 수동 검증:
  - 오디오 로드 (WAV/MP3)
  - 모드 판정 (IDLE/SPEECH/MUSIC)
  - 하이라이트 검출
  - 실시간 루프 (30 FPS, 1초 이상)
  - config 저장/로드 및 검증

## 버전 태깅

- [ ] 버전 번호 결정 (e.g., v0.2.0)
- [ ] 변경사항 요약 작성 (CHANGELOG.md 또는 GitHub Release Notes)
  ```
  Release v0.2.0:
  - 4단계: 오디오 분석 및 모드 판정 (SPEECH/MUSIC/IDLE)
  - 5단계: 하이라이트/드롭 검출 (A안)
  - 5단계 B안: 실시간 루프 (30 FPS)
  - 6단계: Install Wizard (FastAPI 기반 설정 관리)
  - 7단계: Fail-safe + 패키징 + systemd 배포
  ```
- [ ] Git 태그 생성:
  ```bash
  git tag -a v0.2.0 -m "Release v0.2.0 message"
  git push origin v0.2.0
  ```

## 패키징 확인

- [ ] `requirements.txt` 최신화 (새로운 의존성 추가 시)
- [ ] `pyproject.toml` 버전 업데이트 (Option)
- [ ] 배포 파일 준비:
  - [ ] 소스 아카이브: `ai-stage-lighting-system-v0.2.0.tar.gz`
  - [ ] 설치 스크립트: `scripts/install.sh` 검증

## 배포 전 최종 확인

### 개발 VM 환경 시뮬레이션
- [ ] 청정 Ubuntu 20.04+ VM 생성 (또는 컨테이너)
- [ ] 소스 아카이브 압축 해제
- [ ] 설치 스크립트 실행:
  ```bash
  bash scripts/install.sh
  ```
- [ ] 서비스 시작:
  ```bash
  sudo systemctl start handds-engine
  sudo systemctl start handds-web
  ```
- [ ] 서비스 상태 확인:
  ```bash
  sudo systemctl status handds-engine
  sudo systemctl status handds-web
  ```
- [ ] 로그 확인:
  ```bash
  tail -30 /opt/handds/logs/engine.log
  tail -30 /opt/handds/logs/web.log
  ```
- [ ] 웹 UI 접근 확인:
  ```bash
  curl http://localhost:8000/
  ```

## 운영 환경 배포

### Ubuntu Server 호스트에서
- [ ] 프로젝트 디렉터리 생성:
  ```bash
  sudo mkdir -p /opt/handds
  sudo chown -R ubuntu:ubuntu /opt/handds
  ```
- [ ] 소스 코드 배포:
  ```bash
  cd /opt/handds
  tar xzf ../ai-stage-lighting-system-v0.2.0.tar.gz
  ```
- [ ] 설치 실행:
  ```bash
  bash scripts/install.sh
  ```
- [ ] 서비스 활성화 및 시작:
  ```bash
  sudo systemctl enable handds-engine handds-web
  sudo systemctl start handds-engine handds-web
  ```

### 배포 후 검증
- [ ] 부팅 후 자동 시작 확인 (재부팅 후):
  ```bash
  sudo reboot
  # 부팅 완료 후
  sudo systemctl status handds-engine
  sudo systemctl status handds-web
  ```
- [ ] 로그 모니터링 (첫 1시간):
  ```bash
  journalctl -u handds-engine -f
  journalctl -u handds-web -f
  ```
- [ ] 설정 저장/로드 테스트:
  ```bash
  curl http://localhost:8000/api/config
  ```

## 패치/핫픽스 배포 절차

문제 발견 시:
1. 개발 환경에서 수정
2. pytest PASS 확인
3. 영향도 평가 (e.g. failsafe 로직 vs 설정 파일)
4. 패치 버전 증가 (v0.2.1)
5. 해당 파일 또는 전체 재배포

## 롤백 절차

심각한 문제 발생 시:
```bash
systemctl stop handds-engine handds-web
systemctl disable handds-engine handds-web

# 이전 버전으로 복구 또는 설정 초기화
rm /opt/handds/config/install_config.json
# 재배포 또는 부팅 순서대로

systemctl start handds-engine handds-web
```

## 모니터링/로그 관리

### 일상적 모니터링
- [ ] systemd 서비스 상태:
  ```bash
  sudo systemctl is-active handds-engine
  sudo systemctl is-active handds-web
  ```
- [ ] 디스크 공간 (logs 디렉터리):
  ```bash
  du -sh /opt/handds/logs
  ```
- [ ] 프로세스 메모리:
  ```bash
  ps aux | grep -E 'python|uvicorn'
  ```

### 로그 로테이션 (Optional, v2 고려)
- cron job으로 일주일 이상 된 로그 자동 삭제
- systemd journal 압축 설정

---

**마지막 확인**: 모든 항목이 완료되면, 배포 일시와 버전을 기록하고 팀에 공지하세요.
