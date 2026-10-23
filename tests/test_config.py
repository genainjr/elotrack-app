"""Unit tests for configuration manager and enums."""

import os
from pathlib import Path
from unittest.mock import patch

from src.core.config import AudioBitrate, AudioFormat, ConfigManager


class TestConfig:
    def test_audio_format_values(self) -> None:
        values = AudioFormat.values()
        assert "mp3" in values
        assert "wav" in values
        assert "flac" in values
        assert "m4a" in values

    def test_audio_format_is_lossless(self) -> None:
        assert AudioFormat.is_lossless("wav") is True
        assert AudioFormat.is_lossless("flac") is True
        assert AudioFormat.is_lossless("mp3") is False
        assert AudioFormat.is_lossless("m4a") is False

    def test_audio_bitrate_values(self) -> None:
        values = AudioBitrate.values()
        assert "320" in values
        assert "256" in values
        assert "128" in values
        assert "0" in values

    def test_custom_output_dir_override(self, tmp_path: Path) -> None:
        mgr = ConfigManager(custom_output_dir=tmp_path)
        assert mgr.config.default_output_dir == tmp_path.resolve()

    def test_env_var_output_dir_override(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"ELO_TRACK_OUTPUT_DIR": str(tmp_path)}):
            mgr = ConfigManager()
            assert mgr.config.default_output_dir == tmp_path.resolve()
