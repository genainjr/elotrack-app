"""Unit tests for Downloader contract, interfaces, and Open/Closed extensibility."""

from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest
from src.core.downloader import YtDlpAudioDownloader
from src.core.interfaces import (
    AudioProcessor,
    DownloadRequest,
    DownloadResult,
    ProgressEvent,
    ProgressReporter,
    ProgressStatus,
)


class MockProgressReporter(ProgressReporter):
    """Test spy implementation of ProgressReporter."""

    def __init__(self) -> None:
        self.events: List[ProgressEvent] = []
        self.stages: List[tuple[ProgressStatus, str]] = []
        self.errors: List[tuple[Any, str]] = []
        self.completed_result: DownloadResult | None = None

    def on_progress(self, event: ProgressEvent) -> None:
        self.events.append(event)

    def on_stage_changed(self, stage: ProgressStatus, message: str) -> None:
        self.stages.append((stage, message))

    def on_error(self, error: Any, url: str) -> None:
        self.errors.append((error, url))

    def on_complete(self, result: DownloadResult) -> None:
        self.completed_result = result


class MockStemSeparator(AudioProcessor):
    """Simulates a future Demucs/Moises post-processing pipeline step."""

    @property
    def name(self) -> str:
        return "MockStemSeparator"

    def process(self, audio_path: Path, **kwargs: Any) -> Path:
        # Appends simulated stem separation suffix
        stems_dir = audio_path.parent / f"{audio_path.stem}_stems"
        stems_dir.mkdir(exist_ok=True)
        vocals = stems_dir / "vocals.wav"
        vocals.touch()
        return vocals


class TestProgressEvent:
    def test_progress_event_calculations(self) -> None:
        event = ProgressEvent(
            status=ProgressStatus.DOWNLOADING,
            downloaded_bytes=10 * 1024 * 1024,  # 10 MB
            total_bytes=20 * 1024 * 1024,       # 20 MB
            speed_bytes_sec=2 * 1024 * 1024,    # 2 MB/s
            percentage=50.0,
        )
        assert event.downloaded_mb == 10.0
        assert event.total_mb == 20.0
        assert event.speed_mb_sec == 2.0


class TestDownloaderContract:
    def test_rejects_invalid_url_without_downloading(self, tmp_path: Path) -> None:
        downloader = YtDlpAudioDownloader(ffmpeg_path=Path("/fake/ffmpeg"))
        reporter = MockProgressReporter()

        req = DownloadRequest(
            url="https://invalid-site.com/video",
            output_dir=tmp_path,
        )
        result = downloader.download(req, reporter=reporter)

        assert result.success is False
        assert "inválida" in (result.error_message or "").lower()
        assert len(reporter.errors) == 1

    def test_fails_when_ffmpeg_not_available(self, tmp_path: Path) -> None:
        with patch("src.core.validator.EnvironmentValidator.get_ffmpeg_path", return_value=None):
            downloader = YtDlpAudioDownloader(ffmpeg_path=None)
            reporter = MockProgressReporter()

            req = DownloadRequest(
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                output_dir=tmp_path,
            )
            result = downloader.download(req, reporter=reporter)

            assert result.success is False
            assert "FFmpeg" in (result.error_message or "")
            assert len(reporter.errors) == 1

    @patch("yt_dlp.YoutubeDL")
    def test_successful_download_flow(self, mock_ydl_cls: MagicMock, tmp_path: Path) -> None:
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.touch()

        # Simulated downloaded file
        expected_audio_file = tmp_path / "Test Track [dQw4w9WgXcQ].mp3"
        expected_audio_file.write_bytes(b"dummy mp3 data")

        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            "id": "dQw4w9WgXcQ",
            "title": "Test Track",
            "uploader": "Rick Astley",
            "duration": 212,
            "requested_downloads": [{"filepath": str(expected_audio_file)}],
        }
        mock_ydl_cls.return_value.__enter__.return_value = mock_instance

        downloader = YtDlpAudioDownloader(ffmpeg_path=fake_ffmpeg)
        reporter = MockProgressReporter()

        req = DownloadRequest(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=tmp_path,
            audio_format="mp3",
            audio_quality="320",
        )

        result = downloader.download(req, reporter=reporter)

        assert result.success is True
        assert result.title == "Test Track"
        assert result.artist == "Rick Astley"
        assert result.output_path == expected_audio_file
        assert reporter.completed_result == result

        # Verify yt-dlp arguments
        call_opts = mock_ydl_cls.call_args[0][0]
        assert call_opts["format"] == "bestaudio/best"
        assert any(pp["key"] == "FFmpegExtractAudio" and pp["preferredquality"] == "320" for pp in call_opts["postprocessors"])
        assert call_opts["writethumbnail"] is True
        assert any(pp["key"] == "FFmpegMetadata" for pp in call_opts["postprocessors"])
        assert any(pp["key"] == "EmbedThumbnail" for pp in call_opts["postprocessors"])

    @patch("yt_dlp.YoutubeDL")
    def test_open_closed_extensibility_with_audio_processor(self, mock_ydl_cls: MagicMock, tmp_path: Path) -> None:
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.touch()

        raw_audio_file = tmp_path / "Song [dQw4w9WgXcQ].wav"
        raw_audio_file.write_bytes(b"wav raw data")

        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            "id": "dQw4w9WgXcQ",
            "title": "Song",
            "requested_downloads": [{"filepath": str(raw_audio_file)}],
        }
        mock_ydl_cls.return_value.__enter__.return_value = mock_instance

        stem_separator = MockStemSeparator()
        downloader = YtDlpAudioDownloader(ffmpeg_path=fake_ffmpeg)
        reporter = MockProgressReporter()

        req = DownloadRequest(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=tmp_path,
            audio_format="wav",
            post_processors=[stem_separator],
        )

        result = downloader.download(req, reporter=reporter)

        assert result.success is True
        # File path was mutated by the custom processor pipeline
        assert result.output_path is not None
        assert result.output_path.name == "vocals.wav"
        assert any(stage == ProgressStatus.PROCESSING for stage, _ in reporter.stages)

    @patch("yt_dlp.YoutubeDL")
    def test_handles_yt_dlp_download_error(self, mock_ydl_cls: MagicMock, tmp_path: Path) -> None:
        from yt_dlp.utils import DownloadError

        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.touch()

        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = DownloadError("Video unavailable in your country")
        mock_ydl_cls.return_value.__enter__.return_value = mock_instance

        downloader = YtDlpAudioDownloader(ffmpeg_path=fake_ffmpeg)
        reporter = MockProgressReporter()

        req = DownloadRequest(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=tmp_path,
        )

        result = downloader.download(req, reporter=reporter)

        assert result.success is False
        assert "Video unavailable" in (result.error_message or "")
        assert len(reporter.errors) == 1

    @patch("yt_dlp.YoutubeDL")
    def test_flac_download_configuration(self, mock_ydl_cls: MagicMock, tmp_path: Path) -> None:
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.touch()

        flac_audio = tmp_path / "Test FLAC.flac"
        flac_audio.write_bytes(b"dummy flac data")

        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            "id": "dQw4w9WgXcQ",
            "title": "FLAC Song",
            "requested_downloads": [{"filepath": str(flac_audio)}],
        }
        mock_ydl_cls.return_value.__enter__.return_value = mock_instance

        downloader = YtDlpAudioDownloader(ffmpeg_path=fake_ffmpeg)
        req = DownloadRequest(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=tmp_path,
            audio_format="flac",
            embed_thumbnail=True,
        )

        result = downloader.download(req)
        assert result.success is True
        call_opts = mock_ydl_cls.call_args[0][0]
        # FLAC should use lossless postprocessor arg
        assert call_opts["postprocessor_args"]["FFmpegExtractAudio"] == ["-acodec", "flac"]
