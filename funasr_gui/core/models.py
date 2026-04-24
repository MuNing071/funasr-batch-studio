from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".flv",
    ".webm",
    ".m4v",
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
}


FILE_STATES = [
    "Pending",
    "Extracting Audio",
    "Transcribing",
    "Writing Output",
    "Success",
    "Failed",
    "Skipped",
    "Paused",
    "Stopped",
]


@dataclass
class JobSettings:
    input_paths: list[str] = field(default_factory=list)
    output_dir: str = ""
    ffmpeg_bin: str = ""
    preset_name: str = "Balanced"
    model: str = "paraformer-zh"
    vad_model: str = "fsmn-vad"
    punc_model: str = "ct-punc-c"
    device: str = "cpu"
    batch_size_s: int = 300
    hotwords: list[str] = field(default_factory=list)
    skip_existing: bool = True
    overwrite_existing: bool = False
    keep_wav: bool = False
    output_json: bool = True
    output_txt: bool = True
    open_output_when_done: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobSettings":
        return cls(**data)


@dataclass
class FileJob:
    source_path: str
    output_txt_path: str
    output_json_path: str
    state: str = "Pending"
    progress: int = 0
    chars: int = 0
    error: str = ""
    duration_seconds: float | None = None
    started_at: str = ""
    finished_at: str = ""

    def mark_started(self) -> None:
        self.started_at = datetime.now().isoformat(timespec="seconds")

    def mark_finished(self) -> None:
        self.finished_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileJob":
        return cls(**data)


@dataclass
class JobManifest:
    created_at: str
    updated_at: str
    settings: JobSettings
    files: list[FileJob]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": self.settings.to_dict(),
            "files": [item.to_dict() for item in self.files],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobManifest":
        return cls(
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            settings=JobSettings.from_dict(data["settings"]),
            files=[FileJob.from_dict(item) for item in data["files"]],
        )

    @classmethod
    def build(cls, settings: JobSettings, files: list[FileJob]) -> "JobManifest":
        now = datetime.now().isoformat(timespec="seconds")
        return cls(created_at=now, updated_at=now, settings=settings, files=files)

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat(timespec="seconds")


def discover_media_files(input_paths: list[str]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[str] = set()
    for raw_path in input_paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        if path.is_file():
            candidates = [path]
        else:
            candidates = sorted(item for item in path.iterdir() if item.is_file())
        for item in candidates:
            suffix = item.suffix.lower()
            if suffix not in VIDEO_EXTENSIONS:
                continue
            key = str(item.resolve())
            if key in seen:
                continue
            seen.add(key)
            discovered.append(item)
    return sorted(discovered, key=lambda item: item.name.lower())


def build_file_jobs(files: list[Path], output_dir: Path) -> list[FileJob]:
    jobs: list[FileJob] = []
    for file_path in files:
        base_name = file_path.stem
        jobs.append(
            FileJob(
                source_path=str(file_path),
                output_txt_path=str(output_dir / f"{base_name}.txt"),
                output_json_path=str(output_dir / f"{base_name}.json"),
            )
        )
    return jobs
