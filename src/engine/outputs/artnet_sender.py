"""
Art-Net DMX 송신기 (스켈레톤)
- Art-Net 패킷 최소 구조를 만들고 Universe 1에 대한 DMX 데이터(최대 512 바이트)를 송출한다.
- 실제 프로덕션 용도의 모든 필드와 규격을 상세히 구현하지는 않음. 목적은 데이터 흐름 확인용 스켈레톤 제공.

기능:
- send_dmx(host, port, universe, data, dry_run=True)
- generate_dummy_dmx(): 더미 DMX 512 채널 패턴 생성

주의: Art-Net 표준의 일부 필드(ProtVer 등의 엔디안)는 간단화되어 있음.
"""

from __future__ import annotations

import socket
import struct
import logging
from typing import ByteString

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ARTNET_PORT = 6454


class ArtNetSender:
    """Art-Net DMX 송신기 (간단한 스켈레톤)

    실제 장치로 송신하려면 dry_run=False로 설정합니다.
    """

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def close(self) -> None:
        self.sock.close()

    def _build_packet(self, universe: int, data: bytes) -> bytes:
        """간단한 ArtDmx 패킷 빌더 (스켈레톤)

        구조(요약):
        - ID: "Art-Net\0"
        - OpCode: 0x5000 (ArtDmx) (little-endian)
        - ProtVer: 14 (0x000E)
        - Sequence: 0
        - Physical: 0
        - Universe: uint16 (little-endian)
        - Length: uint16 (big-endian) -> DMX 데이터 길이
        - Data: DMX bytes
        """
        # ID
        packet = bytearray(b"Art-Net\x00")
        # OpCode (ArtDmx) - little endian
        packet.extend(struct.pack("<H", 0x5000))
        # ProtVer (hi, lo) : 0x000E -> pack as big-endian unsigned short for simplicity
        packet.extend(struct.pack(">H", 14))
        # Sequence (1), Physical (1)
        packet.extend(b"\x00\x00")
        # Universe (little-endian)
        packet.extend(struct.pack("<H", int(universe) & 0xFFFF))
        # Length (big-endian as per 일부 구현): 실제 Art-Net은 length hi/lo
        length = len(data)
        packet.extend(struct.pack(">H", length & 0xFFFF))
        # Data
        packet.extend(data)
        return bytes(packet)

    def send_dmx(self, host: str, port: int = ARTNET_PORT, universe: int = 0, dmx_data: ByteString | None = None, dry_run: bool = True) -> None:
        """DMX 데이터를 Art-Net으로 송신한다.

        Args:
            host: 목적지 IP
            port: Art-Net 포트 (기본 6454)
            universe: 유니버스 번호
            dmx_data: 최대 512 바이트. None이면 512바이트 0으로 채운다.
            dry_run: True면 실제 송신 대신 로그 출력
        """
        if dmx_data is None:
            dmx_data = bytes([0] * 512)
        if len(dmx_data) > 512:
            raise ValueError("DMX 데이터는 최대 512 바이트여야 합니다")

        # SIM_MODE 설정이 켜져 있으면 DMX 시뮬레이터로 전달
        try:
            from config import settings
        except Exception:
            settings = None

        padded = bytes(dmx_data) + bytes([0] * (512 - len(dmx_data)))

        if settings is not None and getattr(settings, "SIM_MODE", False):
            try:
                from importlib import import_module

                simmod = import_module("src.sim.dmx_simulator")
                DMXSimulator = getattr(simmod, "DMXSimulator")
                sim = DMXSimulator()
                sim.display_universe(universe, padded)
                return
            except Exception as e:
                logger.warning("SIM_MODE 활성화지만 DMX 시뮬레이터 호출 실패: %s", e)

        packet = self._build_packet(universe, padded)

        if dry_run:
            logger.info("[DRY] Art-Net 송신: %s:%d universe=%d bytes=%d", host, port, universe, len(padded))
        else:
            self.sock.sendto(packet, (host, port))

    @staticmethod
    def generate_dummy_dmx() -> bytes:
        """간단한 더미 DMX 패턴 생성: 채널별로 그라데이션을 채움("""
        data = bytearray(512)
        for i in range(512):
            data[i] = (i * 3) & 0xFF
        return bytes(data)


if __name__ == "__main__":
    sender = ArtNetSender()
    dmx = ArtNetSender.generate_dummy_dmx()
    # dry run으로 로그에서 전송 내용 확인
    sender.send_dmx("127.0.0.1", ARTNET_PORT, universe=1, dmx_data=dmx, dry_run=True)
    sender.close()
