"""
특징 추출기

- RMS
- 밴드 에너지 (low/mid/high)
- spectral flux
- onset density

프레임 기반 STFT를 사용하여 특징을 계산한다.
한국어 주석 포함.
"""
from __future__ import annotations

import numpy as np
from scipy import signal
from typing import Dict, Any, Tuple


def frames_from_signal(x: np.ndarray, sr: int, frame_ms: int, hop_ms: int) -> Tuple[np.ndarray, int, int]:
    frame_len = int(sr * frame_ms / 1000)
    hop_len = int(sr * hop_ms / 1000)
    if frame_len <= 0:
        frame_len = 1024
    if hop_len <= 0:
        hop_len = frame_len // 2
    return frame_len, hop_len


def compute_spectrogram(x: np.ndarray, sr: int, n_fft: int, hop_length: int) -> Tuple[np.ndarray, np.ndarray]:
    f, t, Z = signal.stft(x, fs=sr, nperseg=n_fft, noverlap=n_fft - hop_length, boundary=None)
    S = np.abs(Z)
    return f, S


def band_energy_from_spectrogram(f: np.ndarray, S: np.ndarray) -> Dict[str, np.ndarray]:
    """주파수 밴드별 에너지 비율 계산 (low/mid/high)

    밴드 정의:
      low: 20-300 Hz
      mid: 300-2000 Hz
      high: 2000+ Hz
    """
    low_idx = np.where((f >= 20) & (f < 300))[0]
    mid_idx = np.where((f >= 300) & (f < 2000))[0]
    high_idx = np.where(f >= 2000)[0]

    # 각 프레임 별 에너지
    total = np.sum(S, axis=0) + 1e-12
    low_e = np.sum(S[low_idx, :], axis=0) if low_idx.size else np.zeros(S.shape[1])
    mid_e = np.sum(S[mid_idx, :], axis=0) if mid_idx.size else np.zeros(S.shape[1])
    high_e = np.sum(S[high_idx, :], axis=0) if high_idx.size else np.zeros(S.shape[1])

    return {
        "low": low_e / total,
        "mid": mid_e / total,
        "high": high_e / total,
    }


def compute_rms(x: np.ndarray, frame_len: int, hop_len: int) -> np.ndarray:
    """프레임별 RMS 계산"""
    # 제로 패딩
    n_frames = max(1, 1 + (len(x) - frame_len) // hop_len) if len(x) >= frame_len else 1
    rms = np.zeros(n_frames)
    for i in range(n_frames):
        start = i * hop_len
        frame = x[start: start + frame_len]
        if frame.size == 0:
            rms[i] = 0.0
        else:
            rms[i] = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
    return rms


def spectral_flux(S: np.ndarray) -> np.ndarray:
    """스펙트럼 플럭스: 연속 프레임간 양의 변화 합"""
    # 정규화된 스펙트럼
    S_norm = S / (np.sum(S, axis=0, keepdims=True) + 1e-12)
    diff = np.diff(S_norm, axis=1)
    pos_diff = np.clip(diff, a_min=0, a_max=None)
    flux = np.sum(pos_diff, axis=0)
    # 첫 프레임은 0
    flux = np.concatenate(([0.0], flux))
    return flux


def onset_density_from_flux(flux: np.ndarray, threshold: float = 0.02) -> float:
    """온셋 밀도: flux가 threshold를 넘는 프레임 비율 반환"""
    if flux.size == 0:
        return 0.0
    onsets = flux > threshold
    return float(np.sum(onsets) / flux.size)


def extract_features(x: np.ndarray, sr: int, settings: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """오디오 신호로부터 프레임 기반 특징들을 계산하여 반환한다.

    반환값에 포함되는 키:
      - times: 프레임 시간 리스트
      - rms: 프레임별 RMS
      - band_low/mid/high: 프레임별 밴드 비율
      - flux: 프레임별 spectral flux
      - onset_density: 전체 신호에 대한 onset density (스칼라)
    """
    frame_ms = settings.get("FRAME_SIZE_MS", 100)
    hop_ms = settings.get("HOP_SIZE_MS", 50)
    n_fft = settings.get("N_FFT", 2048)

    frame_len, hop_len = frames_from_signal(x, sr, frame_ms, hop_ms)
    f, S = compute_spectrogram(x, sr, n_fft, hop_len)

    # 시간 축
    n_frames = S.shape[1]
    times = np.arange(n_frames) * (hop_len / sr)

    band = band_energy_from_spectrogram(f, S)
    rms = compute_rms(x, frame_len, hop_len)
    # rms 길이와 스펙트럼 프레임 길이 다를 수 있으므로 맞춤
    min_len = min(len(rms), n_frames)
    rms = rms[:min_len]
    # 밴드/flux을 같은 길이로
    for k in list(band.keys()):
        band[k] = band[k][:min_len]
    S = S[:, :min_len]
    f = f

    flux = spectral_flux(S)
    flux = flux[:min_len]

    onset_density = onset_density_from_flux(flux, threshold=0.02)

    return {
        "times": times[:min_len],
        "rms": rms,
        "band_low": band["low"],
        "band_mid": band["mid"],
        "band_high": band["high"],
        "flux": flux,
        "onset_density": onset_density,
    }
