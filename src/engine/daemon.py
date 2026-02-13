"""
데몬 모드: 항상 실행되는 엔진 프로세스

- systemd에서 계속 실행될 수 있도록 설계
- 오디오 입력이 없으면 샘플 sine 파형을 생성하여 데모 모드로 동작
- 30fps realtime loop를 무한으로 유지
- 설정 파일(config/settings.py)을 로드하여 ModeManager/HighlightDetector 초기화
- 시뮬레이터(픽셀/DMX)에 모드와 강도를 전달

한국어 주석 포함
"""
from __future__ import annotations

from typing import Any
import time
import logging
import signal

import numpy as np

from config import settings
from src.engine.features import extract_features
from src.engine.mode_manager import ModeManager
from src.engine.highlight import HighlightDetector
from src.engine.outputs.udp_pixel_sender import UDPPixelSender
from src.web import config_manager

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s - %(levelname)s - %(message)s"
)


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


def _frame_features_from_buffer(
    frame: np.ndarray, sr: int, prev_mag: np.ndarray | None = None
) -> tuple[dict[str, float], np.ndarray | None]:
    """간단한 프레임 기반 특징 계산 (실시간 목표, 가벼운 연산).

    반환: (feat_dict, curr_mag)
    feat keys: rms, band_low, band_mid, band_high, flux
    """
    # RMS
    rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2))) if frame.size > 0 else 0.0

    # FFT 기반 대역 에너지 비율
    n = len(frame)
    if n <= 0:
        return (
            {"rms": rms, "band_low": 0.0, "band_mid": 0.0, "band_high": 0.0, "flux": 0.0},
            None,
        )

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


class DaemonLoop:
    """데몬 루프를 관리하는 클래스"""

    def __init__(self, target_fps: int | None = None, demo_freq: float = 440.0):
        """
        Args:
            target_fps: 처리 프레임 속도 (None이면 settings.TARGET_FPS)
            demo_freq: 데모 sine 파형 주파수 (Hz)
        """
        self.fps = int(target_fps or settings.TARGET_FPS)
        self.sr = settings.SAMPLE_RATE
        self.samples_per_frame = int(
            settings.SAMPLES_PER_FRAME or max(1, int(self.sr / self.fps))
        )
        self.demo_freq = demo_freq
        self.running = True

        # 설정 로드
        self.mm = ModeManager(
            {
                "MODE_HOLD_SECONDS": settings.MODE_HOLD_SECONDS,
                "RMS_SILENCE_THRESHOLD": settings.RMS_SILENCE_THRESHOLD,
                "SPEECH_MID_PROP": settings.SPEECH_MID_PROP,
                "MUSIC_HIGH_PROP": settings.MUSIC_HIGH_PROP,
                "MUSIC_ONSET_DENSITY": settings.MUSIC_ONSET_DENSITY,
            }
        )
        self.detector = HighlightDetector(
            {
                "HIGHLIGHT_THRESHOLD": settings.HIGHLIGHT_THRESHOLD,
                "DROP_THRESHOLD": settings.DROP_THRESHOLD,
                "HIGHLIGHT_HYSTERESIS": settings.HIGHLIGHT_HYSTERESIS,
                "HIGHLIGHT_COOLDOWN_SECONDS": settings.HIGHLIGHT_COOLDOWN_SECONDS,
                "HIGHLIGHT_WEIGHT_RMS": settings.HIGHLIGHT_WEIGHT_RMS,
                "HIGHLIGHT_WEIGHT_BAND_HIGH": settings.HIGHLIGHT_WEIGHT_BAND_HIGH,
                "HIGHLIGHT_WEIGHT_FLUX": settings.HIGHLIGHT_WEIGHT_FLUX,
            }
        )

        self.sender = UDPPixelSender()
        self.demo_time = 0.0
        self.frame_duration = 1.0 / self.fps
        self.prev_mag = None
        self.frames = 0
        self._last_cfg_mtime = None

        logger.info(f"데몬 루프 초기화됨 (FPS: {self.fps}, 샘플레이트: {self.sr})")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """시그널 핸들러: SIGTERM, SIGINT"""
        logger.info(f"신호 {signum} 수신, 종료 중...")
        self.running = False

    def _generate_demo_frame(self) -> np.ndarray:
        """데모용 sine 파형 프레임 생성"""
        t = np.arange(self.samples_per_frame) / self.sr + self.demo_time
        frame = 0.3 * np.sin(2 * np.pi * self.demo_freq * t).astype(np.float32)
        return frame

    def _check_config_reload(self) -> None:
        """설정 파일 변경 감지 및 재로드"""
        cfg_mtime = config_manager.get_config_mtime()
        if cfg_mtime is not None and self._last_cfg_mtime != cfg_mtime:
            try:
                run_cfg = config_manager.load_config()
                logger.info("설정 파일 변경 감지, 재로드됨")
                self._last_cfg_mtime = cfg_mtime
            except Exception as e:
                logger.warning(f"설정 재로드 실패: {e}")

    def _send_pixel_frame(self, mode: str, hstate: str, frame_idx: int) -> None:
        """픽셀 데이터 송출"""
        pixel_count = 64

        if mode == "IDLE":
            ch = 3
            intensity = 0.3
        elif mode == "SPEECH":
            ch = 1
            intensity = 0.7
        else:  # MUSIC
            ch = 0
            if hstate == "HIGHLIGHT":
                intensity = 1.0
            elif hstate == "DROP":
                intensity = 0.3
            else:
                intensity = 0.7

        payload = UDPPixelSender.generate_dummy_pixel_data(pixel_count, ch)
        payload = _adjust_payload_intensity(payload, intensity)
        self.sender.send_frame(
            "127.0.0.1",
            9000 + ch,
            payload,
            output_id=ch + 1,
            frame_index=frame_idx,
            dry_run=True,
        )

    def run(self) -> int:
        """데몬 루프 실행 (무한)

        Returns:
            처리한 총 프레임 수
        """
        # 시그널 핸들러 등록
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("데몬 루프 시작")

        try:
            while self.running:
                loop_start = time.time()

                # 데모용 sine 파형 생성
                frame = self._generate_demo_frame()

                # 특징 계산
                feat, mag = _frame_features_from_buffer(frame, self.sr, self.prev_mag)
                self.prev_mag = mag

                # 설정 재로드 확인
                self._check_config_reload()

                # 모드 및 하이라이트 상태 업데이트
                now = time.time()
                mode = self.mm.update(feat, now=now)
                hstate = self.mm.update_highlight(feat, self.detector, now=now)

                # 픽셀 송출
                self._send_pixel_frame(mode, hstate, self.frames)

                # 프레임 카운터 및 시간 업데이트
                self.frames += 1
                self.demo_time += self.samples_per_frame / self.sr

                # 루프 타이밍 보정
                elapsed = time.time() - loop_start
                sleep_for = self.frame_duration - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

        except Exception as e:
            logger.error(f"데몬 루프 오류: {e}", exc_info=True)
            return 1
        finally:
            self.sender.close()
            logger.info(f"데몬 종료 (처리 프레임: {self.frames})")

        return 0


def run_daemon(target_fps: int | None = None) -> int:
    """데몬 모드 실행

    무한 루프를 유지하며 실시간 모드 판정 및 LED 제어를 수행합니다.
    systemd에서 사용될 엔트리포인트입니다.

    Args:
        target_fps: 처리 프레임 속도 (None이면 settings.TARGET_FPS)

    Returns:
        종료 코드 (정상: 0, 오류: 1)
    """
    loop = DaemonLoop(target_fps=target_fps)
    return loop.run()


if __name__ == "__main__":
    import sys

    exit_code = run_daemon()
    sys.exit(exit_code)
