"""
시뮬레이션 설정

SIM_MODE: True 면 실제 네트워크 송출 대신 시뮬레이터로 전달합니다.
"""

# 기본은 시뮬레이션 모드 켜기 (하드웨어 테스트 전용)
SIM_MODE = True

# 오디오 분석 파라미터
SAMPLE_RATE = 44100
FRAME_SIZE_MS = 100  # 프레임 크기 (ms)
HOP_SIZE_MS = 50     # 홉(프레임 간격) (ms)
N_FFT = 2048

# 특징/임계값 (v1 룰 기반)
RMS_SILENCE_THRESHOLD = 1e-4

# 밴드 비율 임계값 (low/mid/high 비율)
SPEECH_MID_PROP = 0.45   # 중음이 차지하는 비율이 크면 음성 가능성
MUSIC_HIGH_PROP = 0.30   # 고음 비율이 충분히 크면 음악 가능성

# onset / spectral flux 관련
MUSIC_ONSET_DENSITY = 0.08   # 프레임 당 onset 비율이 이 이상이면 음악

# 전이 관련
MODE_HOLD_SECONDS = 0.6   # 새 모드로 바뀌려면 이 시간 동안 연속으로 판단되어야 함
MODE_HYSTERESIS = 0.05    # 기본 히스테리시스 (비율)

# 하이라이트/드롭 검출 (A안)
# highlight_score 계산을 위한 가중치
HIGHLIGHT_WEIGHT_RMS = 0.3
HIGHLIGHT_WEIGHT_BAND_HIGH = 0.3
HIGHLIGHT_WEIGHT_FLUX = 0.4

# 하이라이트/드롭 판정
HIGHLIGHT_THRESHOLD = 0.65  # score >= 이 값이면 하이라이트
DROP_THRESHOLD = 0.25       # score < 이 값이면 드롭
HIGHLIGHT_HYSTERESIS = 0.08 # 히스테리시스 (threshold 주변 반경)

# 쿨다운 (새로운 하이라이트 판정까지의 최소 시간)
HIGHLIGHT_COOLDOWN_SECONDS = 0.3

# 실시간 루프 설정
# 초당 처리 프레임 수 (UI/시뮬 레이트용 기본값)
TARGET_FPS = 30

# 프레임당 최소 샘플 수(명시하지 않으면 SAMPLE_RATE / TARGET_FPS 사용)
# 실시간 목표에 따라 조정 가능
SAMPLES_PER_FRAME = None

# 루프 종료 타임아웃(테스트용 기본값)
REALTIME_LOOP_MAX_SECONDS = None

