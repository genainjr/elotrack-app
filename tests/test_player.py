"""Unit tests for the Audio Player service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.core.player import AudioPlayerService


class TestAudioPlayerService:
    @patch("pygame.mixer.music")
    @patch("pygame.mixer.init")
    def test_audio_player_load_and_play(self, mock_init: MagicMock, mock_music: MagicMock, tmp_path: Path) -> None:
        dummy_audio = tmp_path / "song.mp3"
        dummy_audio.write_bytes(b"dummy mp3 data")

        player = AudioPlayerService()
        ok = player.load(dummy_audio, duration=180.0)
        assert ok is True
        assert player.is_loaded is True
        assert player.duration == 180.0

        play_ok = player.play(start_seconds=15.0)
        assert play_ok is True
        mock_music.play.assert_called_with(start=15.0)

    @patch("pygame.mixer.music")
    @patch("pygame.mixer.init")
    def test_pause_and_stop(self, mock_init: MagicMock, mock_music: MagicMock, tmp_path: Path) -> None:
        dummy_audio = tmp_path / "song.mp3"
        dummy_audio.write_bytes(b"dummy mp3 data")

        player = AudioPlayerService()
        player.load(dummy_audio, duration=100.0)
        mock_music.stop.reset_mock()

        mock_music.get_busy.return_value = True
        player.pause()
        assert player.is_paused is True
        mock_music.pause.assert_called_once()

        player.unpause()
        assert player.is_paused is False
        mock_music.unpause.assert_called_once()

        player.stop()
        mock_music.stop.assert_called_once()
