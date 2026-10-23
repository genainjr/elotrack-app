"""Contracts and interfaces for the Elo Track system.

Follows SOLID principles:
- Single Responsibility: Each interface defines one clear contract.
- Open/Closed: Extensible via AudioProcessor and custom ProgressReporters.
- Liskov Substitution: Any Downloader or Reporter implementation is interchangeable.
- Interface Segregation: Specific protocols for progress reporting and processing.
- Dependency Inversion: High-level modules depend on these abstractions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable


class ProgressStatus(str, Enum):
    """Lifecycle states of the download and extraction process."""

    IDLE = "idle"
    STARTING = "starting"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    PROCESSING = "processing"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ProgressEvent:
    """Immutable data container representing a real-time progress update."""

    status: ProgressStatus
    url: str = ""
    filename: Optional[str] = None
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    percentage: float = 0.0
    speed_bytes_sec: Optional[float] = None
    eta_seconds: Optional[int] = None
    step_description: str = ""
    error: Optional[Exception] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def speed_mb_sec(self) -> Optional[float]:
        """Calculates download speed in MB/s."""
        if self.speed_bytes_sec is not None:
            return self.speed_bytes_sec / (1024 * 1024)
        return None

    @property
    def total_mb(self) -> Optional[float]:
        """Calculates total size in MB."""
        if self.total_bytes is not None:
            return self.total_bytes / (1024 * 1024)
        return None

    @property
    def downloaded_mb(self) -> float:
        """Calculates downloaded size in MB."""
        return self.downloaded_bytes / (1024 * 1024)


@runtime_checkable
class ProgressReporter(Protocol):
    """Protocol for observing download, conversion and processing progress.

    Enables completely decoupled UI adapters (CLI, GUI, Logger, WebSockets).
    """

    def on_progress(self, event: ProgressEvent) -> None:
        """Called whenever progress changes."""
        ...

    def on_stage_changed(self, stage: ProgressStatus, message: str) -> None:
        """Called when a high-level transition occurs (e.g. downloading -> converting)."""
        ...

    def on_error(self, error: Exception | str, url: str) -> None:
        """Called when an unrecoverable error occurs."""
        ...

    def on_complete(self, result: "DownloadResult") -> None:
        """Called when the entire request completes successfully."""
        ...


@runtime_checkable
class AudioProcessor(Protocol):
    """Contract for downstream audio manipulations (trimming, stem separation, normalization).

    Designed to support future extensions like Demucs, Spleeter, or Moises preprocessing
    without modifying the core download pipeline (Open/Closed Principle).
    """

    @property
    def name(self) -> str:
        """Human-readable identifier of the processor."""
        ...

    def process(self, audio_path: Path, **kwargs: Any) -> Path:
        """Processes the input audio file and returns the path to the transformed file."""
        ...


@dataclass
class DownloadRequest:
    """Encapsulates all specifications and optional parameters for an extraction task."""

    url: str
    output_dir: Path
    audio_format: str = "mp3"
    audio_quality: str = "320"
    time_range: Optional[Tuple[int, int]] = None
    custom_filename_template: Optional[str] = None
    post_processors: List[AudioProcessor] = field(default_factory=list)
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    keep_original: bool = False
    download_playlist: bool = False
    extra_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadResult:
    """Structured result returned upon completion of an audio extraction task."""

    success: bool
    url: str
    output_path: Optional[Path] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    duration_seconds: Optional[float] = None
    final_format: Optional[str] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AudioDownloader(Protocol):
    """Abstract contract for audio extraction engines."""

    def download(
        self,
        request: DownloadRequest,
        reporter: Optional[ProgressReporter] = None,
    ) -> DownloadResult:
        """Executes the extraction process based on the supplied request."""
        ...

    def inspect_metadata(self, url: str) -> Dict[str, Any]:
        """Fetches video/audio metadata without initiating download."""
        ...


DownloadProgressCallback = Callable[[ProgressEvent], None]
