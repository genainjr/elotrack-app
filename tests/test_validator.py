"""Unit tests for validation components (Environment, URL, FileSystem)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from src.core.validator import EnvironmentValidator, FileSystemValidator, URLValidator


class TestURLValidator:
    """Verifies YouTube URL pattern matching and ID extraction."""

    @pytest.mark.parametrize(
        "valid_url, expected_id",
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/shorts/dQw4w9WgXcQ?feature=share", "dQw4w9WgXcQ"),
            ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("http://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ],
    )
    def test_valid_youtube_urls(self, valid_url: str, expected_id: str) -> None:
        assert URLValidator.is_valid_youtube_url(valid_url) is True
        assert URLValidator.extract_video_id(valid_url) == expected_id

    def test_clean_video_url_strips_playlist_and_radio_params(self) -> None:
        mix_url = "https://www.youtube.com/watch?v=0TL672ovTpk&list=RD0TL672ovTpk&start_radio=1"
        cleaned = URLValidator.clean_video_url(mix_url)
        assert cleaned == "https://www.youtube.com/watch?v=0TL672ovTpk"

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "",
            None,
            "https://vimeo.com/12345678",
            "https://soundcloud.com/artist/track",
            "not_a_valid_url",
            "https://youtube.com/watch?v=short",  # Less than 11 chars
            "https://google.com",
        ],
    )
    def test_invalid_urls(self, invalid_url: str) -> None:
        assert URLValidator.is_valid_youtube_url(invalid_url) is False
        assert URLValidator.extract_video_id(invalid_url or "") is None


class TestEnvironmentValidator:
    """Verifies FFmpeg presence detection and error messaging."""

    def test_ffmpeg_detected_via_shutil_which(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            path = EnvironmentValidator.get_ffmpeg_path()
            assert path is not None
            assert EnvironmentValidator.is_ffmpeg_available() is True

    def test_ffmpeg_not_found_returns_none(self) -> None:
        with patch("shutil.which", return_value=None), \
             patch("os.name", "posix"):
            path = EnvironmentValidator.get_ffmpeg_path()
            assert path is None
            assert EnvironmentValidator.is_ffmpeg_available() is False

    def test_install_guide_contains_instruction(self) -> None:
        guide = EnvironmentValidator.get_ffmpeg_install_guide()
        assert "winget" in guide or "apt" in guide


class TestFileSystemValidator:
    """Verifies output folder verification and permission checks."""

    def test_valid_directory(self, tmp_path: Path) -> None:
        ok, err = FileSystemValidator.validate_output_directory(tmp_path)
        assert ok is True
        assert err is None

    def test_creates_missing_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "new_folder" / "sub_folder"
        assert not nested.exists()

        ok, err = FileSystemValidator.validate_output_directory(nested, create_if_missing=True)
        assert ok is True
        assert err is None
        assert nested.is_dir()

    def test_fails_on_regular_file_target(self, tmp_path: Path) -> None:
        file_target = tmp_path / "some_file.txt"
        file_target.touch()

        ok, err = FileSystemValidator.validate_output_directory(file_target)
        assert ok is False
        assert "não é uma pasta" in (err or "")
