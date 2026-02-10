import time
import pytest

from src.engine.highlight import HighlightDetector


def make_feat(rms=0.01, band_high=0.3, flux=0.1):
    """테스트 특징값을 구성한다."""
    return {"rms": rms, "band_high": band_high, "flux": flux}


def test_highlight_transitions_on_high_score():
    """높은 점수가 지속될 때 IDLE -> HIGHLIGHT 전환 확인."""
    settings = {
        "HIGHLIGHT_THRESHOLD": 0.65,
        "DROP_THRESHOLD": 0.25,
        # 테스트에서는 쿨다운/히스테리시스를 제거하여 즉시 전이가 발생하도록 함
        "HIGHLIGHT_HYSTERESIS": 0.0,
        "HIGHLIGHT_COOLDOWN_SECONDS": 0.0,
        "HIGHLIGHT_WEIGHT_RMS": 0.3,
        "HIGHLIGHT_WEIGHT_BAND_HIGH": 0.3,
        "HIGHLIGHT_WEIGHT_FLUX": 0.4,
    }

    detector = HighlightDetector(settings)
    now = 1000.0

    # 초기: IDLE 상태
    assert detector.state == "IDLE"

    # 높은 점수의 특징값 계속 공급 (mode="MUSIC"으로 활성화)
    # rms=0.08, band_high=0.7, flux=0.4 => rms_norm=0.8, high_norm=0.7, flux_norm=0.8
    # score = (0.3*0.8 + 0.3*0.7 + 0.4*0.8) / 1.0 = 0.77 > 0.65
    high_feat = make_feat(rms=0.08, band_high=0.7, flux=0.4)
    
    for i in range(3):
        now += 0.05
        state = detector.update(high_feat, "MUSIC", now=now)
    
    # 점수가 높고 충분히 유지되었으므로 HIGHLIGHT로 전환
    assert detector.state == "HIGHLIGHT"


def test_drop_transitions_on_low_score():
    """낮은 점수가 지속될 때 IDLE -> DROP 전환 확인."""
    settings = {
        "HIGHLIGHT_THRESHOLD": 0.65,
        "DROP_THRESHOLD": 0.25,
        # 테스트에서는 쿨다운/히스테리시스를 제거하여 즉시 전이가 발생하도록 함
        "HIGHLIGHT_HYSTERESIS": 0.0,
        "HIGHLIGHT_COOLDOWN_SECONDS": 0.0,
        "HIGHLIGHT_WEIGHT_RMS": 0.3,
        "HIGHLIGHT_WEIGHT_BAND_HIGH": 0.3,
        "HIGHLIGHT_WEIGHT_FLUX": 0.4,
    }

    detector = HighlightDetector(settings)
    now = 2000.0

    # 매우 낮은 점수의 특징값 (mode="MUSIC"으로 활성화)
    # rms=0.001, band_high=0.1, flux=0.05 => rms_norm=0.01, high_norm=0.1, flux_norm=0.1
    # score = (0.3*0.01 + 0.3*0.1 + 0.4*0.1) / 1.0 = 0.067 < 0.25
    low_feat = make_feat(rms=0.001, band_high=0.1, flux=0.05)
    
    for i in range(3):
        now += 0.05
        state = detector.update(low_feat, "MUSIC", now=now)
    
    # 점수가 낮고 충분히 유지되었으므로 DROP으로 전환
    assert detector.state == "DROP"


def test_non_music_mode_stays_idle():
    """MUSIC 모드가 아니면 항상 IDLE을 반환한다."""
    settings = {
        "HIGHLIGHT_THRESHOLD": 0.65,
        "DROP_THRESHOLD": 0.25,
        "HIGHLIGHT_HYSTERESIS": 0.08,
        "HIGHLIGHT_COOLDOWN_SECONDS": 0.1,
        "HIGHLIGHT_WEIGHT_RMS": 0.3,
        "HIGHLIGHT_WEIGHT_BAND_HIGH": 0.3,
        "HIGHLIGHT_WEIGHT_FLUX": 0.4,
    }

    detector = HighlightDetector(settings)

    # 높은 점수 특징값이지만 mode가 SPEECH인 경우
    high_feat = make_feat(rms=0.08, band_high=0.7, flux=0.4)
    state = detector.update(high_feat, "SPEECH", now=1000.0)

    assert state == "IDLE"
    assert detector.state == "IDLE"
