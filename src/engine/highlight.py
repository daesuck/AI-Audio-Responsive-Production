"""
하이라이트/드롭 검출

- RMS, 고음 밴드 에너지, spectral flux를 가중합하여 highlight_score 계산
- 히스테리시스와 쿨다운 적용
- MUSIC 모드에서 활용 (다른 모드에서는 비활성화)

한국어 주석 포함.
"""
from __future__ import annotations

import time
from typing import Dict, Any


class HighlightDetector:
    """음악 신호로부터 하이라이트(강조 구간)와 드롭(약한 구간)을 검출한다.

    상태 머신:
      - IDLE: 초기 상태
      - HIGHLIGHT: 하이라이트 중
      - DROP: 드롭 중
    """

    STATES = ("IDLE", "HIGHLIGHT", "DROP")

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.state = "IDLE"
        self._last_transition_time = None

    def compute_score(self, feat: Dict[str, float]) -> float:
        """특징값들로부터 하이라이트 점수를 계산한다 (0..1 범위).

        Args:
            feat: 특징 딕셔너리. 다음 키 포함: rms, band_high, flux

        Returns:
            점수 (0..1)
        """
        rms = float(feat.get("rms", 0.0))
        band_high = float(feat.get("band_high", 0.0))
        flux = float(feat.get("flux", 0.0))

        # 각 특징을 0..1 범위로 정규화
        # rms: 임의의 상한을 0.1로 가정
        rms_norm = min(1.0, rms / 0.1)
        # band_high: 이미 비율이므로 그대로
        high_norm = band_high
        # flux: 임의의 상한을 0.5로 가정
        flux_norm = min(1.0, flux / 0.5)

        # 가중합
        w_rms = self.settings.get("HIGHLIGHT_WEIGHT_RMS", 0.3)
        w_high = self.settings.get("HIGHLIGHT_WEIGHT_BAND_HIGH", 0.3)
        w_flux = self.settings.get("HIGHLIGHT_WEIGHT_FLUX", 0.4)

        total_weight = w_rms + w_high + w_flux
        if total_weight <= 0:
            total_weight = 1.0

        score = (w_rms * rms_norm + w_high * high_norm + w_flux * flux_norm) / total_weight
        return float(min(1.0, max(0.0, score)))

    def update(self, feat: Dict[str, float], mode: str, now: float | None = None) -> str:
        """특징값을 받아 상태를 업데이트하고 반환한다.

        Args:
            feat: 특징 딕셔너리
            mode: 현재 모드 (\"MUSIC\"일 때만 하이라이트 검출 활성화, 필수 인자)
            now: 현재 시간 (None이면 time.time())

        Returns:
            현재 상태 (\"IDLE\", \"HIGHLIGHT\", \"DROP\")
        """
        now = now if now is not None else time.time()

        # MUSIC 모드가 아니면 항상 IDLE (state 변경, 타이머 초기화 없음)
        if mode != "MUSIC":
            self.state = "IDLE"
            return self.state

        self._last_transition_time = self._last_transition_time or now

        score = self.compute_score(feat)
        threshold = self.settings.get("HIGHLIGHT_THRESHOLD", 0.65)
        drop_thresh = self.settings.get("DROP_THRESHOLD", 0.25)
        hyst = self.settings.get("HIGHLIGHT_HYSTERESIS", 0.08)
        cooldown = self.settings.get("HIGHLIGHT_COOLDOWN_SECONDS", 0.3)
        elapsed = now - self._last_transition_time

        # 히스테리시스 적용
        if self.state == "HIGHLIGHT":
            threshold_go = threshold - hyst
        elif self.state == "DROP":
            threshold_go = drop_thresh + hyst
        else:
            threshold_go = threshold  # IDLE 상태

        # 쿨다운 체크
        if elapsed < cooldown:
            return self.state

        # 상태 전이
        if self.state == "IDLE":
            if score >= threshold:
                self.state = "HIGHLIGHT"
                self._last_transition_time = now
            elif score < drop_thresh:
                self.state = "DROP"
                self._last_transition_time = now
        elif self.state == "HIGHLIGHT":
            if score < threshold_go:
                self.state = "DROP" if score < drop_thresh else "IDLE"
                self._last_transition_time = now
        elif self.state == "DROP":
            if score >= (drop_thresh + hyst):
                self.state = "IDLE"
                self._last_transition_time = now

        return self.state
