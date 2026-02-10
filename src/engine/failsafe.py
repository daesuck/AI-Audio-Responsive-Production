"""
장애 안전(Fail-safe) 정책

네트워크/하드웨어 장애에 대응하는 우아한 강하(graceful shutdown).

정책:
  1. NORMAL: 정상 상태
  2. LAST_HOLD (1.5초): 마지막 정상 신호 유지 (픽셀/DMX 유지)
  3. DIM_AMBIENT (5초): 주변 조명으로 감쇠
  4. DIM_BLACK (15초+): 점진적으로 검정색으로 감쇠 (선택가능)

구현:
  - 프레임 송출 실패 감지(간단히 flag 기반 또는 timeout 기반)
  - 경과 시간에 따라 강도(intensity)를 단계별로 조정
  - 시뮬레이터/실제 송출 모두 입력 강도에 영향을 받도록 설계

한국어 주석 포함.
"""
from __future__ import annotations

import time
from typing import Optional
from enum import Enum


class FailsafeState(Enum):
    """장애 안전 상태 정의"""
    NORMAL = "normal"
    LAST_HOLD = "last_hold"
    DIM_AMBIENT = "dim_ambient"
    DIM_BLACK = "dim_black"


class FailsafeManager:
    """장애 발생 시간을 추적하고 상태별 강도 계산.

    호출 흐름:
      1. on_frame_sent(): 프레임 송출 성공 시 (장애 타이머 리셋)
      2. on_frame_fail(): 프레임 송출 실패 시 (타이머 시작)
      3. get_intensity(): 현재 강도(0..1)를 조회
    """

    def __init__(
        self,
        hold_seconds: float = 1.5,
        ambient_seconds: float = 5.0,
        black_seconds: float = 15.0,
        ambient_intensity: float = 0.2,
        recovery_hold_seconds: float = 0.5,
    ):
        """
        Args:
            hold_seconds: LAST_HOLD 유지 기간 (장애 감지 시)
            ambient_seconds: DIM_AMBIENT 지속 기간
            black_seconds: DIM_BLACK 지속 기간 (음수면 비활성화)
            ambient_intensity: 주변조명 강도 (0..1)
            recovery_hold_seconds: Recovery(정상 신호 재개) 후 안정화 기간
        """
        self.hold_seconds = float(hold_seconds)
        self.ambient_seconds = float(ambient_seconds)
        self.black_seconds = float(black_seconds)
        self.ambient_intensity = float(ambient_intensity)
        self.recovery_hold_seconds = float(recovery_hold_seconds)

        self._failure_time: Optional[float] = None
        self._recovery_time: Optional[float] = None
        self.state = FailsafeState.NORMAL

    def on_frame_sent(self, now: Optional[float] = None) -> None:
        """프레임 송출 성공: 장애 해제 및 recovery 상태 진입.

        장애 중이었다면 recovery 신호로 해제되고, NORMAL 상태로 복귀.
        플래핑 방지를 위해 recovery_hold_seconds 동안 안정화 기간 추적 (선택적 사용).
        """
        now = now if now is not None else time.time()
        if self._failure_time is not None:
            # 기존 장애를 recovery 신호로 해제
            self._failure_time = None
            self._recovery_time = now
            self.state = FailsafeState.NORMAL

    def on_frame_fail(self, now: Optional[float] = None) -> None:
        """프레임 송출 실패: 장애 카운터 시작, LAST_HOLD 상태 진입"""
        now = now if now is not None else time.time()
        if self._failure_time is None:
            self._failure_time = now
            self.state = FailsafeState.LAST_HOLD

    def get_intensity(self, now: Optional[float] = None) -> float:
        """현재 강도를 반환 (0..1).

        - NORMAL: 1.0
        - LAST_HOLD: 1.0 (유지)
        - DIM_AMBIENT: ambient_intensity로 감쇠
        - DIM_BLACK: 0.0으로 선형 감쇠
        """
        now = now if now is not None else time.time()

        if self._failure_time is None:
            self.state = FailsafeState.NORMAL
            return 1.0

        elapsed = now - self._failure_time

        # 상태 결정
        if elapsed < self.hold_seconds:
            self.state = FailsafeState.LAST_HOLD
            return 1.0
        elif elapsed < self.hold_seconds + self.ambient_seconds:
            self.state = FailsafeState.DIM_AMBIENT
            return self.ambient_intensity
        elif self.black_seconds > 0 and elapsed < self.hold_seconds + self.ambient_seconds + self.black_seconds:
            self.state = FailsafeState.DIM_BLACK
            # 선형 감쇠: ambient_intensity -> 0.0
            progress = (elapsed - self.hold_seconds - self.ambient_seconds) / self.black_seconds
            return self.ambient_intensity * (1.0 - progress)
        else:
            # 전체 시간 경과: 완전히 꺼짐
            self.state = FailsafeState.DIM_BLACK
            return 0.0

    def get_state_str(self) -> str:
        """현재 상태를 문자열로 반환"""
        return self.state.value
