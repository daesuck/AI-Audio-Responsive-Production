"""
픽셀 시뮬레이터 (콘솔 출력)

- 최대 4채널, 채널당 최대 1024 픽셀을 지원
- 1D 스트립 형태로 간단히 콘솔에 표시

목적: 네트워크/하드웨어 없이 픽셀 데이터 흐름을 눈으로 확인
"""

from __future__ import annotations

import math
from typing import ByteString


class PixelSimulator:
    """콘솔 기반 픽셀 시뮬레이터"""

    def __init__(self, max_pixels: int = 1024) -> None:
        self.max_pixels = max_pixels

    def _luminance_char(self, r: int, g: int, b: int) -> str:
        """픽셀 밝기를 10단계 문자로 매핑"""
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        levels = " .:-=+*#%@"
        idx = int((lum / 255.0) * (len(levels) - 1))
        return levels[idx]

    def display_frame(self, output_id: int, pixel_payload: ByteString, frame_index: int = 0) -> None:
        """픽셀 프레임을 콘솔에 표시한다.

        Args:
            output_id: 출력 식별자 (채널 번호)
            pixel_payload: RGB 바이트 스트림
            frame_index: 프레임 인덱스
        """
        pixel_count = int(len(pixel_payload) / 3)
        pixel_count = min(pixel_count, self.max_pixels)

        # 한 줄에 표시할 픽셀 수 제한 (콘솔 폭 고려)
        display_width = min(128, pixel_count)

        # 요약 라인
        print(f"[PIXEL_SIM] output={output_id} frame={frame_index} pixels={pixel_count}")

        # 축약해서 표시: 시작~끝 일부를 포함
        step = max(1, pixel_count // display_width)
        chars = []
        for i in range(0, pixel_count, step):
            idx = i * 3
            r = pixel_payload[idx]
            g = pixel_payload[idx + 1]
            b = pixel_payload[idx + 2]
            chars.append(self._luminance_char(r, g, b))

        # 출력
        print("".join(chars))
        print("\n")


if __name__ == "__main__":
    # 간단한 데모: 64픽셀 더미 생성
    from src.engine.outputs.udp_pixel_sender import UDPPixelSender

    sim = PixelSimulator()
    payload = UDPPixelSender.generate_dummy_pixel_data(64, 0)
    sim.display_frame(1, payload, frame_index=0)
