"""Core domain and infrastructure for Elo Track."""

from .config import AppConfig, AudioBitrate, AudioFormat, ConfigManager
from .downloader import YtDlpAudioDownloader
from .interfaces import (
    AudioDownloader,
    AudioProcessor,
    DownloadProgressCallback,
    DownloadRequest,
    DownloadResult,
    ProgressEvent,
    ProgressReporter,
    ProgressStatus,
)
from .validator import EnvironmentValidator, FileSystemValidator, URLValidator

__all__ = [
    "AppConfig",
    "AudioBitrate",
    "AudioDownloader",
    "AudioFormat",
    "AudioProcessor",
    "ConfigManager",
    "DownloadProgressCallback",
    "DownloadRequest",
    "DownloadResult",
    "EnvironmentValidator",
    "FileSystemValidator",
    "ProgressEvent",
    "ProgressReporter",
    "ProgressStatus",
    "URLValidator",
    "YtDlpAudioDownloader",
]
