"""
오디오 입력 로더 (WAV / MP3 지원)

이 모듈은 파일 확장자에 따라 적절한 로더를 사용하여 오디오를 읽고
float32 범위로 정규화하여 반환한다. 가능한 경우 `librosa`를 사용해 다양한
포맷을 지원하며, 설치되어 있지 않으면 WAV는 `scipy`로 읽고 mp3 계열은
사용자에게 의존성 설치를 안내한다.

리샘플링은 `target_sr`이 주어졌을 때 `scipy.signal.resample`로 처리한다.
한국어 주석으로 작성됨.
"""
from __future__ import annotations

from typing import Tuple
import os
import subprocess
import shutil

import numpy as np
from scipy.io import wavfile
from scipy import signal


def _to_float32(data: np.ndarray) -> np.ndarray:
    """정수형 오디오를 -1..1 범위의 float32로 변환"""
    if data.dtype == np.int16:
        return (data.astype(np.float32) / 32768.0).astype(np.float32)
    if data.dtype == np.int32:
        return (data.astype(np.float32) / 2147483648.0).astype(np.float32)
    if data.dtype == np.uint8:
        return ((data.astype(np.float32) - 128.0) / 128.0).astype(np.float32)
    return data.astype(np.float32)


def _resample_if_needed(x: np.ndarray, orig_sr: int, target_sr: int) -> Tuple[np.ndarray, int]:
    if target_sr is None or orig_sr == target_sr:
        return x, orig_sr
    # scipy.signal.resample을 이용한 간단한 리샘플링
    new_len = int(round(len(x) * (target_sr / float(orig_sr))))
    if new_len <= 0:
        return x, orig_sr
    if x.ndim == 1:
        y = signal.resample(x, new_len)
    else:
        # 다중 채널이면 채널별로 리샘플
        chans = []
        for ch in range(x.shape[1]):
            chans.append(signal.resample(x[:, ch], new_len))
        y = np.stack(chans, axis=1)
    return y.astype(np.float32), target_sr


def load_audio(path: str, target_sr: int = 44100, mono: bool = True) -> Tuple[np.ndarray, int]:
    """오디오 파일을 로드하여 (samples, sr)을 반환

    Args:
        path: 오디오 파일 경로 (.wav, .mp3 등)
        target_sr: 출력 샘플레이트 (None이면 원본 유지)
        mono: True면 모노로 변환

    Returns:
        samples (float32, -1..1), sr

    Notes:
        - 가능한 경우 `librosa`를 사용하여 다양한 포맷을 지원합니다.
        - `librosa`가 없으면 WAV는 scipy로 읽어옵니다. mp3 처리를 위해서는
          `librosa` 또는 외부 디코더(ffmpeg)가 필요합니다.
    """
    ext = os.path.splitext(path)[1].lower()

    # WAV는 scipy로 처리
    if ext == ".wav":
        sr, data = wavfile.read(path)
        data = _to_float32(data)
        if mono and data.ndim > 1:
            data = np.mean(data, axis=1)
        data, sr = _resample_if_needed(data, sr, target_sr)
        return data, sr

    # MP3: ffmpeg를 사용하여 PCM(s16le)로 디코드하여 읽음
    if ext == ".mp3":
        # ffmpeg 존재 확인
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "mp3 파일을 로드하려면 시스템에 'ffmpeg'가 필요합니다.\n"
                "Windows 사용자는 https://ffmpeg.org/ 에서 ffmpeg를 설치하고 PATH에 추가하세요."
            )

        # ffmpeg 명령 구성
        channels = 1 if mono else 2
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            path,
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ac",
            str(channels),
        ]
        if target_sr is not None:
            cmd += ["-ar", str(int(target_sr))]
        cmd += ["-"]

        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="ignore") if hasattr(e, "stderr") else ""
            raise RuntimeError(f"ffmpeg 실행 실패: {stderr}")

        raw = proc.stdout
        # s16le -> int16
        arr = np.frombuffer(raw, dtype=np.int16)
        if channels > 1 and arr.size > 0:
            arr = arr.reshape(-1, channels)
            if mono:
                data = np.mean(arr, axis=1)
            else:
                data = arr
        else:
            data = arr

        data = _to_float32(data)
        sr = int(target_sr) if target_sr is not None else 44100
        return data, sr

    # 지원되지 않는 확장자
    raise RuntimeError(f"지원되지 않는 오디오 포맷: {ext}")

