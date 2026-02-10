import numpy as np

from src.engine.main import run_realtime


def test_realtime_runs_one_second():
    # 1초짜리 더미 신호 (사인파)
    sr = 44100
    t = np.linspace(0, 1.0, int(sr * 1.0), endpoint=False)
    x = 0.01 * np.sin(2 * np.pi * 440.0 * t).astype(np.float32)

    # 루프를 1초까지만 실행하도록 max_seconds 지정
    frames = run_realtime(x=x, sr=sr, target_fps=30, max_seconds=1.0)

    # 최소 한 프레임 이상 처리되어야 함
    assert frames >= 1
