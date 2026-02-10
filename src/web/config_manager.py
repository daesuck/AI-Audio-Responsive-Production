"""
간단한 설치 구성 저장/로드 및 검증기

- 파일: config/install_config.json
- 검증: DMX 주소 중복, 전체 DMX 채널 수 <= 512, pixel_count 범위 검사

한국어 주석 포함.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "install_config.json")


def load_config() -> Dict[str, Any]:
    """설정 파일을 로드(존재하지 않으면 빈 dict 반환)"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_config(cfg: Dict[str, Any]) -> None:
    """설정 파일 저장 (디렉터리 생성 포함)"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _validate_fixtures(fixtures: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    used_addresses: List[int] = []
    total_channels = 0
    for fx in fixtures:
        start = int(fx.get("start_address", 0))
        mode = fx.get("channel_mode", "1")
        # 간단히 채널 수 추정: mode '1' -> 1채널, '3' -> 3채널 등
        try:
            channels = int(mode)
        except Exception:
            channels = 1

        if start < 1 or start > 512:
            errors.append(f"DMX 시작주소 범위오류: {start}")

        # 채널 주소 배열
        addresses = list(range(start, min(513, start + channels)))
        for a in addresses:
            if a in used_addresses:
                errors.append(f"DMX 주소 중복: {a}")
            else:
                used_addresses.append(a)

        total_channels += channels

    if total_channels > 512:
        errors.append(f"총 DMX 채널 수 초과: {total_channels} > 512")

    return errors


def _validate_pixels(pixels: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    for p in pixels:
        cnt = int(p.get("pixel_count", 0))
        if cnt < 0 or cnt > 1024:
            errors.append(f"pixel_count 범위오류: output_id={p.get('output_id')} count={cnt}")
    return errors


def validate_config(cfg: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """설정 딕셔너리의 기본 검증을 수행하고 (ok, errors)를 반환한다."""
    errors: List[str] = []
    stage = cfg.get("stage", {})
    if not isinstance(stage, dict):
        errors.append("stage 정보가 잘못되었습니다")

    fixtures = cfg.get("dmx_fixtures", []) or []
    if fixtures and not isinstance(fixtures, list):
        errors.append("dmx_fixtures 형식 오류")
    else:
        errors.extend(_validate_fixtures(fixtures))

    pixels = cfg.get("pixel_channels", []) or []
    if pixels and not isinstance(pixels, list):
        errors.append("pixel_channels 형식 오류")
    else:
        errors.extend(_validate_pixels(pixels))

    # audio, profile 등의 기본 필드 존재성은 선택적
    ok = len(errors) == 0
    return ok, errors


def get_config_mtime() -> float | None:
    try:
        return os.path.getmtime(CONFIG_PATH)
    except Exception:
        return None
