import shutil
import pytest

from src.engine import audio_in


def test_mp3_raises_when_no_ffmpeg(monkeypatch):
    """ffmpeg가 없을 때 .mp3 로드 시 친절한 한글 에러 메시지를 발생시키는지 확인한다.

    실제 mp3 파일이 없어도 되도록 ffmpeg 존재 확인을 흉내낸다.
    """
    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError) as exc:
        audio_in.load_audio("dummy.mp3", target_sr=44100, mono=True)

    msg = str(exc.value)
    assert "ffmpeg" in msg or "설치" in msg or "mp3 파일" in msg
