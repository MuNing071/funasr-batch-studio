from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_default_ffmpeg_path() -> str:
    candidate = PROJECT_ROOT / "bin" / "ffmpeg.exe"
    if candidate.exists():
        return str(candidate)
    return "ffmpeg"


def get_app_state_dir() -> Path:
    override = os.environ.get("FUNASR_BATCH_STUDIO_HOME")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "FunASRBatchStudio"
    return Path.home() / ".funasr_batch_studio"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
