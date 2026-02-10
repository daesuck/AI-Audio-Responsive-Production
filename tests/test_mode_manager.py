import time

from src.engine.mode_manager import ModeManager


def make_feat(rms=0.01, low=0.2, mid=0.5, high=0.3, onset=0.01):
    return {"rms": rms, "band_low": low, "band_mid": mid, "band_high": high, "onset_density": onset}


def test_idle_to_music_transition():
    settings = {
        "RMS_SILENCE_THRESHOLD": 1e-4,
        "SPEECH_MID_PROP": 0.45,
        "MUSIC_HIGH_PROP": 0.25,
        "MUSIC_ONSET_DENSITY": 0.05,
        "MODE_HOLD_SECONDS": 0.2,
    }

    mm = ModeManager(settings)

    # 초기: IDLE 상태
    assert mm.current_mode == "IDLE"

    now = 1000.0

    # 몇 프레임 MUSIC 조건을 지속적으로 공급 (hold 초과)
    music_feat = make_feat(rms=0.02, low=0.1, mid=0.2, high=0.7, onset=0.2)
    for i in range(5):
        now += 0.06
        mm.update(music_feat, now=now)

    assert mm.current_mode == "MUSIC"


def test_no_transition_if_not_held():
    settings = {
        "RMS_SILENCE_THRESHOLD": 1e-4,
        "SPEECH_MID_PROP": 0.45,
        "MUSIC_HIGH_PROP": 0.25,
        "MUSIC_ONSET_DENSITY": 0.05,
        "MODE_HOLD_SECONDS": 0.5,
    }

    mm = ModeManager(settings)
    now = 2000.0

    music_feat = make_feat(rms=0.02, low=0.1, mid=0.2, high=0.7, onset=0.2)
    # 간헐적으로 제공: 충분히 유지되지 않음
    now += 0.1
    mm.update(music_feat, now=now)
    now += 0.1
    mm.update(make_feat(rms=0.00001, low=0.8, mid=0.1, high=0.1, onset=0.0), now=now)
    now += 0.1
    mm.update(music_feat, now=now)

    # hold 시간이 충분히 흐르지 않았으므로 전환되지 않아야 함
    assert mm.current_mode != "MUSIC"
