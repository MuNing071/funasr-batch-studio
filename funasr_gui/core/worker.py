from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from .models import FileJob, JobManifest
from .transcriber import BatchTranscriber


class TranscriptionWorker(QObject):
    file_updated = Signal(str, str, int, str, int)
    lifecycle = Signal(str)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, manifest: JobManifest, manifest_path: Path) -> None:
        super().__init__()
        self.manifest = manifest
        self.manifest_path = manifest_path
        self.transcriber = BatchTranscriber(
            manifest=manifest,
            manifest_path=manifest_path,
            progress_callback=self._handle_progress,
        )

    @Slot()
    def run(self) -> None:
        self.lifecycle.emit("running")
        try:
            self.transcriber.process()
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.lifecycle.emit("idle")
            self.finished.emit()

    @Slot()
    def request_pause(self) -> None:
        self.transcriber.request_pause()
        self.lifecycle.emit("pausing")

    @Slot()
    def request_resume(self) -> None:
        self.transcriber.request_resume()
        self.lifecycle.emit("running")

    @Slot()
    def request_stop(self) -> None:
        self.transcriber.request_stop()
        self.lifecycle.emit("stopping")

    def _handle_progress(self, file_job: FileJob, state: str, progress: int, message: str) -> None:
        self.file_updated.emit(file_job.source_path, state, progress, message, file_job.chars)
