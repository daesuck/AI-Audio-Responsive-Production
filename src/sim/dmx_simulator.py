"""
DMX 시뮬레이터 (콘솔 출력)

- DMX Universe 1 (512채널)을 테이블/로그로 표시

목적: Art-Net/DMX 송출 데이터 흐름을 하드웨어 없이 확인
"""

from __future__ import annotations

from typing import ByteString


class DMXSimulator:
    """콘솔 기반 DMX 시뮬레이터"""

    def __init__(self, channels: int = 512) -> None:
        self.channels = channels

    def display_universe(self, universe: int, dmx_data: ByteString) -> None:
        """DMX 유니버스 데이터를 콘솔에 요약 출력한다."""
        length = min(len(dmx_data), self.channels)
        print(f"[DMX_SIM] universe={universe} channels={length}")

        # 주요 통계
        nonzero = sum(1 for v in dmx_data[:length] if v)
        mx = max(dmx_data[:length]) if length > 0 else 0
        mn = min(dmx_data[:length]) if length > 0 else 0
        print(f"  nonzero={nonzero} min={mn} max={mx}")

        # 첫 48 채널을 12열로 표 형태 출력
        to_display = min(length, 48)
        cols = 12
        for r in range(0, to_display, cols):
            row = dmx_data[r : r + cols]
            nums = [f"{(r + i + 1):03d}:{val:03d}" for i, val in enumerate(row)]
            print("  " + " ".join(nums))

        print("\n")


if __name__ == "__main__":
    from src.engine.outputs.artnet_sender import ArtNetSender

    sim = DMXSimulator()
    dmx = ArtNetSender.generate_dummy_dmx()
    sim.display_universe(1, dmx)
