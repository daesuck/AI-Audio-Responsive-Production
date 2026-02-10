from src.web.config_manager import validate_config


def test_dmx_address_duplicate():
    cfg = {
        "dmx_fixtures": [
            {"id": "f1", "start_address": 1, "channel_mode": "3"},
            {"id": "f2", "start_address": 2, "channel_mode": "1"},
        ]
    }
    ok, errors = validate_config(cfg)
    assert not ok
    assert any("중복" in e or "중복" in e for e in errors)


def test_dmx_total_channels_overflow():
    # 두 개의 300채널 장치 -> 600 total -> overflow
    cfg = {
        "dmx_fixtures": [
            {"id": "a", "start_address": 1, "channel_mode": "300"},
            {"id": "b", "start_address": 301, "channel_mode": "300"},
        ]
    }
    ok, errors = validate_config(cfg)
    assert not ok
    assert any("총 DMX 채널 수 초과" in e for e in errors)


def test_pixel_count_range():
    cfg = {"pixel_channels": [{"output_id": 1, "pixel_count": 2000}]}
    ok, errors = validate_config(cfg)
    assert not ok
    assert any("pixel_count" in e for e in errors)
