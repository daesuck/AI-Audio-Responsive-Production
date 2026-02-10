"""
UDP Pixel 프레임 송신기
- 프레임 헤더: output_id(uint16), pixel_count(uint16), frame_index(uint32), chunk_index(uint16), total_chunks(uint16)
- 페이로드: RGB 바이트 스트림 (R,G,B) * pixel_count
- MTU를 고려한 chunk 분할 전송 지원

이 파일은 프로토콜과 데이터 흐름 확인용 스켈레톤 구현입니다.
"""

from __future__ import annotations

import math
import socket
import struct
import logging
from importlib import import_module
from typing import Optional
from typing import Tuple

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 헤더 포맷 (네트워크 바이트 순서: big-endian)
# output_id: uint16, pixel_count: uint16, frame_index: uint32, chunk_index: uint16, total_chunks: uint16
_HEADER_FMT = "!HHIHH"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)

DEFAULT_MTU = 1400  # 보수적으로 설정


class UDPPixelSender:
    """UDP Pixel 프레임 송신기

    기본 사용법:
        sender = UDPPixelSender(mtu=1400)
        sender.send_frame("127.0.0.1", 9000, pixel_bytes, output_id=1, frame_index=0)

    Note: 기본적으로 `dry_run=True`로 실제 네트워크 전송 대신 로그 출력합니다.
    실제 전송하려면 dry_run=False로 설정하세요.
    """

    def __init__(self, mtu: int = DEFAULT_MTU) -> None:
        self.mtu = mtu
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def close(self) -> None:
        self.sock.close()

    def _chunk_payload(self, payload: bytes) -> Tuple[int, int, int]:
        max_payload_per_packet = max(1, self.mtu - _HEADER_SIZE)
        total_chunks = math.ceil(len(payload) / max_payload_per_packet)
        return max_payload_per_packet, total_chunks, len(payload)

    def send_frame(self, host: str, port: int, pixel_payload: bytes, output_id: int = 0, frame_index: int = 0, dry_run: bool = True) -> None:
        """픽셀 프레임을 여러 UDP 패킷으로 분할 전송한다.

        Args:
            host: 목적지 IP
            port: 목적지 포트
            pixel_payload: RGB 바이트 스트림 (len == pixel_count * 3)
            output_id: 출력 식별자
            frame_index: 프레임 인덱스
            dry_run: True이면 전송하지 않고 로그만 출력
        """
        pixel_count = int(len(pixel_payload) / 3)

        # SIM_MODE 설정이 켜져 있으면 시뮬레이터로 전달
        try:
            from config import settings
        except Exception:
            settings = None

        if settings is not None and getattr(settings, "SIM_MODE", False):
            # 시뮬레이터를 동적으로 import (순환 참조 방지)
            try:
                simmod = import_module("src.sim.pixel_simulator")
                PixelSimulator = getattr(simmod, "PixelSimulator")
                sim = PixelSimulator()
                sim.display_frame(output_id, pixel_payload, frame_index=frame_index)
                return
            except Exception as e:
                logger.warning("SIM_MODE 활성화지만 시뮬레이터 호출 실패: %s", e)

        max_payload_per_packet, total_chunks, _ = self._chunk_payload(pixel_payload)

        logger.info("전송 시작: %s:%d output_id=%d pixel_count=%d frame_index=%d total_chunks=%d mtu=%d",
                    host, port, output_id, pixel_count, frame_index, total_chunks, self.mtu)

        offset = 0
        for chunk_index in range(total_chunks):
            chunk = pixel_payload[offset: offset + max_payload_per_packet]
            header = struct.pack(_HEADER_FMT, int(output_id) & 0xFFFF, int(pixel_count) & 0xFFFF, int(frame_index) & 0xFFFFFFFF, int(chunk_index) & 0xFFFF, int(total_chunks) & 0xFFFF)
            packet = header + chunk

            if dry_run:
                logger.info("[DRY] 송신 패킷: output=%d frame=%d chunk=%d/%d bytes=%d", output_id, frame_index, chunk_index + 1, total_chunks, len(packet))
            else:
                self.sock.sendto(packet, (host, int(port)))

            offset += len(chunk)

    @staticmethod
    def generate_dummy_pixel_data(pixel_count: int, channel_index: int = 0) -> bytes:
        """더미 패턴 생성: 각 채널별로 서로 다른 색상 패턴을 생성한다.

        간단한 규칙:
        - 채널 인덱스 0: 레드 그라데이션
        - 채널 인덱스 1: 그린 그라데이션
        - 채널 인덱스 2: 블루 그라데이션
        - 채널 인덱스 3: 화이트/펄스
        """
        data = bytearray()
        for i in range(pixel_count):
            t = int((i / max(1, pixel_count - 1)) * 255)
            if channel_index == 0:
                r, g, b = t, 0, 0
            elif channel_index == 1:
                r, g, b = 0, t, 0
            elif channel_index == 2:
                r, g, b = 0, 0, t
            else:
                # 채널 3 : 색상 섞기
                r, g, b = t, 255 - t, (t * 2) & 255
            data.extend([r & 0xFF, g & 0xFF, b & 0xFF])
        return bytes(data)


if __name__ == "__main__":
    # 간단한 시뮬레이션: 4채널 각각 localhost의 서로 다른 포트로 더미 데이터 전송 (dry_run=True -> 로그 확인)
    sender = UDPPixelSender(mtu=1200)
    pixel_count = 64
    for ch in range(4):
        payload = UDPPixelSender.generate_dummy_pixel_data(pixel_count, ch)
        sender.send_frame("127.0.0.1", 9000 + ch, payload, output_id=ch + 1, frame_index=0, dry_run=True)
    sender.close()
