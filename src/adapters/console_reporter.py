"""Console/Terminal implementation of the ProgressReporter interface."""

from __future__ import annotations

import sys
from typing import Optional

from ..core.interfaces import (
    DownloadResult,
    ProgressEvent,
    ProgressReporter,
    ProgressStatus,
)

# Ensure Windows terminal doesn't crash on utf-8 characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ConsoleProgressReporter(ProgressReporter):
    """Renders real-time download and audio extraction progress directly to stdout/stderr.

    Features:
    - Dynamic in-place terminal progress bar.
    - Human-readable byte formatting (KB, MB, GB).
    - Friendly status indicators and graceful fallback for non-TTY environments.
    """

    def __init__(self, bar_length: int = 25, use_colors: bool = True) -> None:
        self.bar_length = bar_length
        self.is_tty = sys.stdout.isatty()
        self.use_colors = use_colors and self.is_tty
        self._last_line_len = 0

    def _color(self, text: str, color_code: str) -> str:
        if not self.use_colors:
            return text
        return f"\033[{color_code}m{text}\033[0m"

    @staticmethod
    def _format_bytes(bytes_count: Optional[float]) -> str:
        if bytes_count is None or bytes_count < 0:
            return "--"
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_count < 1024.0:
                return f"{bytes_count:3.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"

    @staticmethod
    def _format_time(seconds: Optional[int]) -> str:
        if seconds is None:
            return "--:--"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def on_stage_changed(self, stage: ProgressStatus, message: str) -> None:
        prefix = {
            ProgressStatus.STARTING: self._color("[PREPARANDO]", "36"),  # Cyan
            ProgressStatus.DOWNLOADING: self._color("[DOWNLOAD]", "34"),  # Blue
            ProgressStatus.CONVERTING: self._color("[CONVERSAO]", "33"),  # Yellow
            ProgressStatus.PROCESSING: self._color("[PIPELINE]", "35"),   # Magenta
            ProgressStatus.FINISHED: self._color("[SUCESSO]", "32"),      # Green
            ProgressStatus.ERROR: self._color("[ERRO]", "31"),            # Red
        }.get(stage, "[INFO]")

        if self.is_tty:
            sys.stdout.write("\r" + " " * self._last_line_len + "\r")
        print(f"{prefix} {message}")
        sys.stdout.flush()

    def on_progress(self, event: ProgressEvent) -> None:
        if event.status != ProgressStatus.DOWNLOADING:
            return

        pct = event.percentage
        filled_length = int(self.bar_length * (pct / 100))
        bar = "#" * filled_length + "-" * (self.bar_length - filled_length)

        downloaded_str = self._format_bytes(event.downloaded_bytes)
        total_str = self._format_bytes(event.total_bytes)
        speed_str = (
            f"{self._format_bytes(event.speed_bytes_sec)}/s"
            if event.speed_bytes_sec
            else "--"
        )
        eta_str = self._format_time(event.eta_seconds)

        line = (
            f"\r{self._color('[BAIXANDO]', '34')} [{bar}] "
            f"{pct:5.1f}% ({downloaded_str} / {total_str}) "
            f"Vel: {speed_str} ETA: {eta_str}"
        )

        self._last_line_len = len(line)

        if self.is_tty:
            sys.stdout.write(line)
            sys.stdout.flush()

    def on_complete(self, result: DownloadResult) -> None:
        if self.is_tty:
            sys.stdout.write("\r" + " " * self._last_line_len + "\r")

        title = result.title or "Audio extraido"
        artist = f" por {result.artist}" if result.artist else ""
        path = result.output_path or "Desconhecido"
        size = self._format_bytes(result.file_size_bytes)

        tag = self._color("[OK] CONCLUIDO COM SUCESSO", "1;32")
        print(f"\n{tag}")
        print(f"  - Faixa:     {title}{artist}")
        print(f"  - Arquivo:   {path}")
        print(f"  - Tamanho:   {size} (Formato: {result.final_format})")
        if result.duration_seconds:
            print(f"  - Duracao:   {self._format_time(int(result.duration_seconds))}")
        print()
        sys.stdout.flush()

    def on_error(self, error: Exception | str, url: str) -> None:
        if self.is_tty:
            sys.stdout.write("\r" + " " * self._last_line_len + "\r")

        tag = self._color("[ERRO] FALHA NA EXTRACAO", "1;31")
        msg = str(error)
        print(f"\n{tag}")
        print(f"  - URL:  {url}")
        print(f"  - Motivo: {msg}\n")
        sys.stdout.flush()
