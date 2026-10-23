"""Unit tests for GUI progress adapter."""

from pathlib import Path

from src.adapters.gui_reporter import GuiProgressReporter
from src.core.interfaces import DownloadResult, ProgressEvent, ProgressStatus


class TestGuiReporter:
    def test_gui_reporter_dispatches_callbacks(self) -> None:
        received = {}

        def on_prog(ev: ProgressEvent) -> None:
            received["prog"] = ev.percentage

        def on_stg(st: ProgressStatus, msg: str) -> None:
            received["stage"] = (st, msg)

        def on_comp(res: DownloadResult) -> None:
            received["comp"] = res.success

        def on_err(err: str, url: str) -> None:
            received["err"] = err

        reporter = GuiProgressReporter(
            progress_callback=on_prog,
            stage_callback=on_stg,
            complete_callback=on_comp,
            error_callback=on_err,
        )

        reporter.on_progress(ProgressEvent(status=ProgressStatus.DOWNLOADING, percentage=75.5))
        assert received["prog"] == 75.5

        reporter.on_stage_changed(ProgressStatus.CONVERTING, "Convertendo...")
        assert received["stage"] == (ProgressStatus.CONVERTING, "Convertendo...")

        res = DownloadResult(success=True, url="http://youtube.com/test", output_path=Path("song.mp3"))
        reporter.on_complete(res)
        assert received["comp"] is True

        reporter.on_error("Falha", "http://youtube.com/test")
        assert received["err"] == "Falha"
