from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Callable

from .models import FileJob, JobManifest, JobSettings
from .storage import save_manifest, save_recent_manifest

ProgressCallback = Callable[[FileJob, str, int, str], None]


class BatchTranscriber:
    def __init__(
        self,
        manifest: JobManifest,
        manifest_path: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.manifest = manifest
        self.manifest_path = manifest_path
        self.progress_callback = progress_callback
        self._should_stop = False
        self._should_pause = False
        self._model = None

    def request_stop(self) -> None:
        self._should_stop = True

    def request_pause(self) -> None:
        self._should_pause = True

    def request_resume(self) -> None:
        self._should_pause = False

    def process(self) -> None:
        settings = self.manifest.settings
        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = output_dir / "_wav_tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        save_recent_manifest(self.manifest_path)

        self._load_model(settings)

        for file_job in self.manifest.files:
            if self._should_stop:
                self._update(file_job, "Stopped", file_job.progress, "Stopped by user")
                continue

            while self._should_pause:
                self._update(file_job, "Paused", file_job.progress, "Paused")
                time.sleep(0.2)

            self._process_file(file_job, settings, temp_dir)

    def _load_model(self, settings: JobSettings) -> None:
        if self._model is not None:
            return
        from funasr import AutoModel

        hotword = "\n".join(settings.hotwords).strip() or None
        self._model = AutoModel(
            model=settings.model,
            vad_model=settings.vad_model or None,
            punc_model=settings.punc_model or None,
            device=settings.device,
            disable_update=True,
            hotword=hotword,
        )

    def _process_file(self, file_job: FileJob, settings: JobSettings, temp_dir: Path) -> None:
        txt_path = Path(file_job.output_txt_path)
        json_path = Path(file_job.output_json_path)

        if settings.skip_existing and self._is_success_output(txt_path):
            self._update(file_job, "Skipped", 100, "Skipped existing transcript")
            return

        if not settings.overwrite_existing and txt_path.exists() and not settings.skip_existing:
            self._update(file_job, "Failed", 100, "Output exists and overwrite is disabled")
            return

        source_path = Path(file_job.source_path)
        safe_wav_name = hashlib.md5(str(source_path).encode("utf-8")).hexdigest() + ".wav"
        wav_path = temp_dir / safe_wav_name

        file_job.mark_started()
        started = time.monotonic()

        try:
            if source_path.suffix.lower() in {".wav", ".mp3", ".m4a", ".flac"}:
                wav_input = source_path
            else:
                self._update(file_job, "Extracting Audio", 5, "Extracting audio")
                self._extract_audio(settings.ffmpeg_bin, source_path, wav_path)
                wav_input = wav_path

            self._update(file_job, "Transcribing", 25, "Running FunASR")
            result = self._model.generate(
                input=str(wav_input),
                batch_size_s=settings.batch_size_s,
            )

            self._update(file_job, "Writing Output", 85, "Writing transcript")
            text = self._extract_text(result)
            file_job.chars = len(text)
            if settings.output_txt:
                txt_path.write_text(text, encoding="utf-8")
            if settings.output_json:
                json_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            file_job.duration_seconds = round(time.monotonic() - started, 2)
            file_job.error = ""
            file_job.mark_finished()
            self._update(file_job, "Success", 100, f"Completed, {file_job.chars} chars")
        except Exception as exc:
            file_job.error = str(exc)
            file_job.mark_finished()
            if settings.output_txt:
                txt_path.write_text(f"[ERROR]\n{exc}\n", encoding="utf-8")
            self._update(file_job, "Failed", 100, str(exc))
        finally:
            if wav_path.exists() and not settings.keep_wav:
                try:
                    wav_path.unlink()
                except OSError:
                    pass

    def _update(self, file_job: FileJob, state: str, progress: int, message: str) -> None:
        file_job.state = state
        file_job.progress = progress
        save_manifest(self.manifest_path, self.manifest)
        if self.progress_callback is not None:
            self.progress_callback(file_job, state, progress, message)

    @staticmethod
    def _is_success_output(txt_path: Path) -> bool:
        if not txt_path.exists() or txt_path.stat().st_size <= 0:
            return False
        head = txt_path.read_text(encoding="utf-8", errors="ignore")[:64]
        return not head.startswith("[ERROR]")

    @staticmethod
    def _extract_audio(ffmpeg_bin: str, source_path: Path, wav_path: Path) -> None:
        command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            str(wav_path),
        ]
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"ffmpeg failed for {source_path.name}: {stderr[-800:]}")

    @staticmethod
    def _extract_text(result: list[dict]) -> str:
        if not result:
            return ""
        from funasr.utils.postprocess_utils import rich_transcription_postprocess

        text = result[0].get("text", "")
        if not text:
            return ""
        return rich_transcription_postprocess(text)
