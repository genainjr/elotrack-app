"""GUI progress reporter adapter for decoupled Tkinter/CustomTkinter updates."""

from __future__ import annotations

from typing import Callable, Optional

from ..core.interfaces import (
    DownloadResult,
    ProgressEvent,
    ProgressReporter,
    ProgressStatus,
)


class GuiProgressReporter(ProgressReporter):
    """Bridges core download events to GUI callbacks thread-safely."""

    def __init__(
        self,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        stage_callback: Optional[Callable[[ProgressStatus, str], None]] = None,
        complete_callback: Optional[Callable[[DownloadResult], None]] = None,
        error_callback: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self._progress_cb = progress_callback
        self._stage_cb = stage_callback
        self._complete_cb = complete_callback
        self._error_cb = error_callback

    def on_progress(self, event: ProgressEvent) -> None:
        if self._progress_cb:
            self._progress_cb(event)

    def on_stage_changed(self, stage: ProgressStatus, message: str) -> None:
        if self._stage_cb:
            self._stage_cb(stage, message)

    def on_complete(self, result: DownloadResult) -> None:
        if self._complete_cb:
            self._complete_cb(result)

    def on_error(self, error: Exception | str, url: str) -> None:
        if self._error_cb:
            self._error_cb(str(error), url)
