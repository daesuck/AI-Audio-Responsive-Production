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

