"""
메인 분석 루프

- WAV 파일을 읽어서 프레임 단위로 특징을 계산
- `ModeManager`로 모드 판정
- `HighlightDetector`로 MUSIC 모드의 하이라이트/드롭 검출 (A안)
- 시뮬레이터(픽셀/DMX)에 모드와 강도를 전달 (네트워크 송출은 비활성화)

한국어 주석 및 간단한 실행용 API 제공
"""
from __future__ import annotations

from typing import Any
import time
import logging

import numpy as np

from config import settings
from src.engine.audio_in import load_audio
from src.engine.features import extract_features
from src.engine.mode_manager import ModeManager
from src.engine.highlight import HighlightDetector
from src.engine.outputs.udp_pixel_sender import UDPPixelSender

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _adjust_payload_intensity(pixel_data: bytes, intensity: float) -> bytes:
    """픽셀 데이터의 밝기(intensity)를 조정한다.

    Args:
        pixel_data: RGB 바이트 시퀀스
        intensity: 0..1 범위 강도 배수

    Returns:
        조정된 픽셀 데이터
    """
    intensity = max(0.0, min(1.0, intensity))
    if intensity == 1.0:
        return pixel_data

    arr = bytearray(pixel_data)
    for i in range(0, len(arr), 3):
        r = int(arr[i] * intensity) & 0xFF
        g = int(arr[i + 1] * intensity) & 0xFF
        b = int(arr[i + 2] * intensity) & 0xFF
        arr[i] = r
        arr[i + 1] = g
        arr[i + 2] = b
    return bytes(arr)


def run_analysis(audio_path: str) -> None:
    """오디오 파일 전체를 분석하고 시뮬레이터에 모드 및 강도 결과를 전달한다."""
    x, sr = load_audio(audio_path)
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
        # A안 파라미터
        "HIGHLIGHT_THRESHOLD": settings.HIGHLIGHT_THRESHOLD,
        "DROP_THRESHOLD": settings.DROP_THRESHOLD,
        "HIGHLIGHT_HYSTERESIS": settings.HIGHLIGHT_HYSTERESIS,
        "HIGHLIGHT_COOLDOWN_SECONDS": settings.HIGHLIGHT_COOLDOWN_SECONDS,
        "HIGHLIGHT_WEIGHT_RMS": settings.HIGHLIGHT_WEIGHT_RMS,
        "HIGHLIGHT_WEIGHT_BAND_HIGH": settings.HIGHLIGHT_WEIGHT_BAND_HIGH,
        "HIGHLIGHT_WEIGHT_FLUX": settings.HIGHLIGHT_WEIGHT_FLUX,
    }

    feats = extract_features(x, sr, cfg)
    times = feats.get("times", np.array([]))
    rms = feats.get("rms", np.array([]))
    flux = feats.get("flux", np.array([]))

    mm = ModeManager(cfg)
    detector = HighlightDetector(cfg)

    sender = UDPPixelSender()

    # 프레임별로 모드 업데이트 및 하이라이트 검출, 시뮬레이터 호출
    for i, t in enumerate(times):
        feat = {
            "rms": float(rms[i]) if i < len(rms) else 0.0,
            "band_low": float(feats["band_low"][i]) if i < len(feats["band_low"]) else 0.0,
            "band_mid": float(feats["band_mid"][i]) if i < len(feats["band_mid"]) else 0.0,
            "band_high": float(feats["band_high"][i]) if i < len(feats["band_high"]) else 0.0,
            "onset_density": float(feats.get("onset_density", 0.0)),
            "flux": float(flux[i]) if i < len(flux) else 0.0,
        }

        mode = mm.update(feat, now=time.time())
        hlight_state = mm.update_highlight(feat, detector, now=time.time())

        # 시뮬레이터에 mode를 반영 (간단하게 pixel 패턴 전송)
        # 실제 네트워크 전송은 disabled (dry_run=True)
        pixel_count = 64
        if mode == "IDLE":
            ch = 3
            intensity = 0.3
        elif mode == "SPEECH":
            ch = 1
            intensity = 0.7
        else:  # MUSIC
            ch = 0
            # 하이라이트 상태에 따라 강도 조정
            if hlight_state == "HIGHLIGHT":
                intensity = 1.0
            elif hlight_state == "DROP":
                intensity = 0.3
            else:  # IDLE (normal music)
                intensity = 0.7

        payload = UDPPixelSender.generate_dummy_pixel_data(pixel_count, ch)
        # 강도 적용
        payload = _adjust_payload_intensity(payload, intensity)
        sender.send_frame("127.0.0.1", 9000 + ch, payload, output_id=ch + 1, frame_index=i, dry_run=True)

    sender.close()


def _frame_features_from_buffer(frame: np.ndarray, sr: int, prev_mag: np.ndarray | None = None):
    """간단한 프레임 기반 특징 계산 (실시간 목표, 가벼운 연산).

    반환: (feat_dict, curr_mag)
    feat keys: rms, band_low, band_mid, band_high, flux
    """
    # RMS
    rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2))) if frame.size > 0 else 0.0

    # FFT 기반 대역 에너지 비율
    n = len(frame)
    if n <= 0:
        return ({"rms": rms, "band_low": 0.0, "band_mid": 0.0, "band_high": 0.0, "flux": 0.0}, None)

    # 윈도잉
    win = np.hanning(n)
    spec = np.fft.rfft(frame * win)
    mag = np.abs(spec)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)

    total = mag.sum() + 1e-12
    low_idx = (freqs >= 20) & (freqs < 300)
    mid_idx = (freqs >= 300) & (freqs < 2000)
    high_idx = freqs >= 2000

    low_e = float(mag[low_idx].sum() / total) if low_idx.any() else 0.0
    mid_e = float(mag[mid_idx].sum() / total) if mid_idx.any() else 0.0
    high_e = float(mag[high_idx].sum() / total) if high_idx.any() else 0.0

    # spectral flux (양의 변화 합)
    if prev_mag is None or prev_mag.shape != mag.shape:
        flux = 0.0
    else:
        diff = mag - prev_mag
        pos = diff.clip(min=0.0)
        flux = float(pos.sum() / (prev_mag.sum() + 1e-12))

    feat = {"rms": rms, "band_low": low_e, "band_mid": mid_e, "band_high": high_e, "flux": flux}
    return feat, mag


def run_realtime(x: np.ndarray | None = None, sr: int | None = None, audio_path: str | None = None, target_fps: int | None = None, max_seconds: float | None = None) -> int:
    """실시간 루프: audio -> features -> mode -> highlight -> simulator

    Args:
        x, sr: 메모리내 오디오 데이터 (float32, mono) 제공 가능
        audio_path: 파일 경로를 주면 로드
        target_fps: 처리 프레임 속도 (None이면 settings.TARGET_FPS)
        max_seconds: 루프 최대 동작 시간 (None이면 settings.REALTIME_LOOP_MAX_SECONDS)

    Returns:
        처리한 프레임 수
    """
    if audio_path is not None:
        x, sr = load_audio(audio_path)

    if x is None or sr is None:
        raise ValueError("오디오 입력(x,sr) 또는 audio_path 중 하나는 필요합니다.")

    fps = int(target_fps or settings.TARGET_FPS)
    samples_per_frame = int(settings.SAMPLES_PER_FRAME or max(1, int(sr / fps)))
    max_seconds = max_seconds if max_seconds is not None else settings.REALTIME_LOOP_MAX_SECONDS

    mm = ModeManager({
        "MODE_HOLD_SECONDS": settings.MODE_HOLD_SECONDS,
        "RMS_SILENCE_THRESHOLD": settings.RMS_SILENCE_THRESHOLD,
        "SPEECH_MID_PROP": settings.SPEECH_MID_PROP,
        "MUSIC_HIGH_PROP": settings.MUSIC_HIGH_PROP,
        "MUSIC_ONSET_DENSITY": settings.MUSIC_ONSET_DENSITY,
    })
    detector = HighlightDetector({
        "HIGHLIGHT_THRESHOLD": settings.HIGHLIGHT_THRESHOLD,
        "DROP_THRESHOLD": settings.DROP_THRESHOLD,
        "HIGHLIGHT_HYSTERESIS": settings.HIGHLIGHT_HYSTERESIS,
        "HIGHLIGHT_COOLDOWN_SECONDS": settings.HIGHLIGHT_COOLDOWN_SECONDS,
        "HIGHLIGHT_WEIGHT_RMS": settings.HIGHLIGHT_WEIGHT_RMS,
        "HIGHLIGHT_WEIGHT_BAND_HIGH": settings.HIGHLIGHT_WEIGHT_BAND_HIGH,
        "HIGHLIGHT_WEIGHT_FLUX": settings.HIGHLIGHT_WEIGHT_FLUX,
    })

    sender = UDPPixelSender()

    n_samples = len(x)
    read_pos = 0
    frame_duration = 1.0 / fps
    prev_mag = None
    frames = 0
    start_time = time.time()

    while True:
        loop_start = time.time()

        # 종료 조건: 최대 시간
        if max_seconds is not None and (loop_start - start_time) >= max_seconds:
            break

        # 오디오 읽기
        end = min(read_pos + samples_per_frame, n_samples)
        frame = x[read_pos:end]
        # 제로패딩
        if frame.size < samples_per_frame:
            pad = np.zeros(samples_per_frame - frame.size, dtype=frame.dtype)
            frame = np.concatenate((frame, pad))

        feat, mag = _frame_features_from_buffer(frame, sr, prev_mag)
        prev_mag = mag

        # 모드/하이라이트 업데이트
        now = time.time()
        mode = mm.update(feat, now=now)
        hstate = mm.update_highlight(feat, detector, now=now)

        # 시뮬레이터 반영 (강도 조정)
        pixel_count = 64
        if mode == "IDLE":
            ch = 3
            intensity = 0.3
        elif mode == "SPEECH":
            ch = 1
            intensity = 0.7
        else:
            ch = 0
            if hstate == "HIGHLIGHT":
                intensity = 1.0
            elif hstate == "DROP":
                intensity = 0.3
            else:
                intensity = 0.7

        payload = UDPPixelSender.generate_dummy_pixel_data(pixel_count, ch)
        payload = _adjust_payload_intensity(payload, intensity)
        sender.send_frame("127.0.0.1", 9000 + ch, payload, output_id=ch + 1, frame_index=frames, dry_run=True)

        frames += 1
        read_pos = end
        if read_pos >= n_samples:
            # 오디오 끝 도달하면 루프 종료
            break

        # 루프 타이밍 보정
        elapsed = time.time() - loop_start
        sleep_for = frame_duration - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)

    sender.close()
    return frames


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.engine.main path/to/file.wav")
    else:
        run_analysis(sys.argv[1])
