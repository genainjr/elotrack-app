"""Configuration manager and defaults for Elo Track."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Set


class AudioFormat(str, Enum):
    """Supported audio container formats."""

    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    M4A = "m4a"
    OPUS = "opus"
    OGG = "ogg"

    @classmethod
    def values(cls) -> Set[str]:
        return {item.value for item in cls}

    @classmethod
    def is_lossless(cls, fmt: str) -> bool:
        return fmt.lower() in {cls.WAV.value, cls.FLAC.value}


class AudioBitrate(str, Enum):
    """Common target bitrates (kbps) for lossy encoders."""

    B320 = "320"
    B256 = "256"
    B192 = "192"
    B128 = "128"
    BEST = "0"  # yt-dlp highest VBR/lossless representation

    @classmethod
    def values(cls) -> Set[str]:
        return {item.value for item in cls}


@dataclass
class AppConfig:
    """Application-wide settings and default parameters."""

    default_output_dir: Path
    default_format: AudioFormat = AudioFormat.MP3
    default_bitrate: AudioBitrate = AudioBitrate.B320
    default_stream_selector: str = "bestaudio/best"
    ffmpeg_binary_path: Optional[Path] = None
    max_retries: int = 3
    socket_timeout: int = 30
    filename_template: str = "%(title)s.%(ext)s"
    log_level: int = logging.INFO


class ConfigManager:
    """Centralizes directory configuration, codec definitions, and environment variables."""

    _instance: Optional[ConfigManager] = None
    _config: Optional[AppConfig] = None

    def __init__(self, custom_output_dir: Optional[Path] = None) -> None:
        self._config = self._build_config(custom_output_dir)

    @classmethod
    def get_instance(cls, custom_output_dir: Optional[Path] = None) -> ConfigManager:
        if cls._instance is None:
            cls._instance = ConfigManager(custom_output_dir)
        return cls._instance

    @property
    def config(self) -> AppConfig:
        assert self._config is not None
        return self._config

    def _build_config(self, custom_output_dir: Optional[Path] = None) -> AppConfig:
        env_output = os.getenv("ELO_TRACK_OUTPUT_DIR")
        if custom_output_dir:
            output_dir = Path(custom_output_dir).expanduser().resolve()
        elif env_output:
            output_dir = Path(env_output).expanduser().resolve()
        else:
            # Prefer system Music directory if available, otherwise ./downloads
            music_dir = Path.home() / "Music" / "EloTrack"
            output_dir = music_dir if music_dir.parent.exists() else Path("./downloads").resolve()

        custom_ffmpeg = os.getenv("FFMPEG_PATH")
        ffmpeg_path = Path(custom_ffmpeg).resolve() if custom_ffmpeg else None

        log_level_name = os.getenv("ELO_TRACK_LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_name, logging.INFO)

        return AppConfig(
            default_output_dir=output_dir,
            ffmpeg_binary_path=ffmpeg_path,
            log_level=log_level,
        )

    @staticmethod
    def configure_logging(level: int = logging.INFO, structured: bool = False) -> None:
        """Sets up structured console logging for the core module."""
        fmt = (
            "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
            if structured
            else "[%(levelname)s] %(message)s"
        )
        logging.basicConfig(level=level, format=fmt, force=True)
