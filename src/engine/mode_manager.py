"""
모드 매니저: SPEECH / MUSIC / IDLE 판정 (룰 기반)

히스테리시스와 최소 유지 시간(hold)을 적용한다.
한국어 주석 포함.
"""
from __future__ import annotations

import time
from typing import Dict, Any


class ModeManager:
    """간단한 상태 머신으로 모드를 판정한다.

    판정 입력: 프레임별 특징값들 (딕셔너리) — 예: 'rms', 'band_low', 'band_mid', 'band_high', 'onset_density'
    """

    MODES = ("IDLE", "SPEECH", "MUSIC")

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.current_mode = "IDLE"
        self._candidate = None
        self._candidate_since = None

    def _score_modes(self, feat: Dict[str, float]) -> Dict[str, float]:
        # 간단 점수 규칙
        low = float(feat.get("band_low", 0.0))
        mid = float(feat.get("band_mid", 0.0))
        high = float(feat.get("band_high", 0.0))
        rms = float(feat.get("rms", 0.0))
        onset = float(feat.get("onset_density", 0.0))

        scores = {m: 0.0 for m in self.MODES}

        # IDLE: RMS가 매우 낮으면 우선
        if rms < self.settings.get("RMS_SILENCE_THRESHOLD", 1e-5):
            scores["IDLE"] += 1.0

        # SPEECH: mid 비율이 크고 onset이 낮은 편
        if mid > self.settings.get("SPEECH_MID_PROP", 0.45) and onset < self.settings.get("MUSIC_ONSET_DENSITY", 0.08):
            scores["SPEECH"] += 1.0 + (mid - self.settings.get("SPEECH_MID_PROP", 0.45))

        # MUSIC: onset density 높고 high 비율도 어느정도
        if onset > self.settings.get("MUSIC_ONSET_DENSITY", 0.08) and high > self.settings.get("MUSIC_HIGH_PROP", 0.30):
            scores["MUSIC"] += 1.0 + (onset - self.settings.get("MUSIC_ONSET_DENSITY", 0.08))

        # 보조: high가 매우 큰 경우 MUSIC 가중
        if high > 0.5:
            scores["MUSIC"] += 0.5

        return scores

    def update(self, feat: Dict[str, float], now: float | None = None) -> str:
        """현재 프레임의 특징을 받아 모드를 업데이트하고 반환한다."""
        now = now if now is not None else time.time()
        scores = self._score_modes(feat)
        # 가장 높은 점수 모드 선택
        candidate = max(scores.items(), key=lambda x: x[1])[0]

        # 후보가 바뀌었으면 타이머 리셋
        if candidate != self._candidate:
            self._candidate = candidate
            self._candidate_since = now

        # 만약 후보가 현재 모드와 같으면 유지
        if candidate == self.current_mode:
            return self.current_mode

        # 후보가 일정 시간 유지되면 전환
        hold = float(self.settings.get("MODE_HOLD_SECONDS", 0.6))
        if (now - (self._candidate_since or now)) >= hold and candidate != self.current_mode:
            self.current_mode = candidate
            return self.current_mode

        return self.current_mode
