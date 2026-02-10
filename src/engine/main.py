"""
메인 분석 루프

- WAV 파일을 읽어서 프레임 단위로 특징을 계산
- `ModeManager`로 모드 판정
- 시뮬레이터(픽셀/DMX)에 현재 모드를 전달 (네트워크 송출은 비활성화)

한국어 주석 및 간단한 실행용 API 제공
"""
from __future__ import annotations

from typing import Any
import time
import logging

import numpy as np

from config import settings
from src.engine.audio_in import load_wav
from src.engine.features import extract_features
from src.engine.mode_manager import ModeManager
from src.engine.outputs.udp_pixel_sender import UDPPixelSender

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_analysis(wav_path: str) -> None:
    """WAV 파일 전체를 분석하고 시뮬레이터에 모드 결과를 전달한다."""
    x, sr = load_wav(wav_path)
    # 설정에서 파라미터 읽기
    cfg = {
        "FRAME_SIZE_MS": settings.FRAME_SIZE_MS,
        "HOP_SIZE_MS": settings.HOP_SIZE_MS,
        "N_FFT": settings.N_FFT,
        "RMS_SILENCE_THRESHOLD": settings.RMS_SILENCE_THRESHOLD,
        "SPEECH_MID_PROP": settings.SPEECH_MID_PROP,
        "MUSIC_HIGH_PROP": settings.MUSIC_HIGH_PROP,
        "MUSIC_ONSET_DENSITY": settings.MUSIC_ONSET_DENSITY,
        "MODE_HOLD_SECONDS": settings.MODE_HOLD_SECONDS,
    }

    feats = extract_features(x, sr, cfg)
    times = feats.get("times", np.array([]))
    rms = feats.get("rms", np.array([]))

    mm = ModeManager(cfg)

    sender = UDPPixelSender()

    # 프레임별로 모드 업데이트 및 시뮬레이터 호출
    for i, t in enumerate(times):
        feat = {
            "rms": float(rms[i]) if i < len(rms) else 0.0,
            "band_low": float(feats["band_low"][i]) if i < len(feats["band_low"]) else 0.0,
            "band_mid": float(feats["band_mid"][i]) if i < len(feats["band_mid"]) else 0.0,
            "band_high": float(feats["band_high"][i]) if i < len(feats["band_high"]) else 0.0,
            "onset_density": float(feats.get("onset_density", 0.0)),
        }

        mode = mm.update(feat, now=time.time())

        # 시뮬레이터에 mode를 반영 (간단하게 pixel 패턴 전송)
        # 실제 네트워크 전송은 disabled (dry_run=True)
        pixel_count = 64
        if mode == "IDLE":
            ch = 3
        elif mode == "SPEECH":
            ch = 1
        else:
            ch = 0

        payload = UDPPixelSender.generate_dummy_pixel_data(pixel_count, ch)
        sender.send_frame("127.0.0.1", 9000 + ch, payload, output_id=ch + 1, frame_index=i, dry_run=True)

    sender.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.engine.main path/to/file.wav")
    else:
        run_analysis(sys.argv[1])
