import pytest
import time
from src.engine.failsafe import FailsafeManager, FailsafeState


def test_failsafe_normal_state():
    """정상 상태에서는 항상 강도 1.0"""
    fsm = FailsafeManager()
    
    # 프레임 송출 성공 (정상)
    fsm.on_frame_sent(now=0.0)
    assert fsm.get_intensity(now=0.0) == 1.0
    assert fsm.state == FailsafeState.NORMAL


def test_failsafe_last_hold():
    """장애 발생 후 1.5초 동안 LAST_HOLD (강도 1.0 유지)"""
    fsm = FailsafeManager(hold_seconds=1.5, ambient_seconds=5.0, black_seconds=15.0)
    
    # 장애 시작
    fsm.on_frame_fail(now=0.0)
    
    # 0.5초: 아직 LAST_HOLD
    intensity = fsm.get_intensity(now=0.5)
    assert intensity == 1.0
    assert fsm.state == FailsafeState.LAST_HOLD
    
    # 1.5초: 정확히 경계 (전환 직전, 여전히 LAST_HOLD)
    intensity = fsm.get_intensity(now=1.49)
    assert intensity == 1.0


def test_failsafe_dim_ambient():
    """1.5초 후 DIM_AMBIENT로 전환 (ambient_intensity = 0.2)"""
    fsm = FailsafeManager(hold_seconds=1.5, ambient_seconds=5.0, ambient_intensity=0.2)
    
    fsm.on_frame_fail(now=0.0)
    
    # 1.6초: DIM_AMBIENT 상태, 강도 = 0.2
    intensity = fsm.get_intensity(now=1.6)
    assert fsm.state == FailsafeState.DIM_AMBIENT
    assert intensity == pytest.approx(0.2, abs=0.01)


def test_failsafe_recovery():
    """프레임 송출 성공 시 상태 복구"""
    fsm = FailsafeManager()
    
    # 장애 발생
    fsm.on_frame_fail(now=0.0)
    assert fsm.state == FailsafeState.LAST_HOLD
    
    # 복구
    fsm.on_frame_sent(now=0.5)
    assert fsm.state == FailsafeState.NORMAL
    assert fsm.get_intensity(now=0.5) == 1.0
