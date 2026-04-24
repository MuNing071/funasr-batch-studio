from __future__ import annotations

import json
from pathlib import Path

from .models import JobManifest, JobSettings
from .paths import ensure_directory, get_app_state_dir, get_default_ffmpeg_path


APP_STATE_DIR = get_app_state_dir()
SETTINGS_PATH = APP_STATE_DIR / "settings.json"
VOCAB_PRESETS_PATH = APP_STATE_DIR / "vocabulary_presets.json"
RECENT_MANIFESTS_PATH = APP_STATE_DIR / "recent_manifests.json"


def ensure_state_dir() -> None:
    ensure_directory(APP_STATE_DIR)


def load_settings() -> JobSettings:
    ensure_state_dir()
    if not SETTINGS_PATH.exists():
        return JobSettings(ffmpeg_bin=get_default_ffmpeg_path())
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    settings = JobSettings.from_dict(data)
    if not settings.ffmpeg_bin:
        settings.ffmpeg_bin = get_default_ffmpeg_path()
    return settings


def save_settings(settings: JobSettings) -> None:
    ensure_state_dir()
    SETTINGS_PATH.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_vocab_presets() -> dict[str, list[str]]:
    ensure_state_dir()
    if not VOCAB_PRESETS_PATH.exists():
        return {}
    return json.loads(VOCAB_PRESETS_PATH.read_text(encoding="utf-8"))


def save_vocab_presets(presets: dict[str, list[str]]) -> None:
    ensure_state_dir()
    VOCAB_PRESETS_PATH.write_text(
        json.dumps(presets, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_manifest(manifest_path: Path, manifest: JobManifest) -> None:
    manifest.touch()
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_manifest(manifest_path: Path) -> JobManifest:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return JobManifest.from_dict(data)


def load_recent_manifests() -> list[str]:
    ensure_state_dir()
    if not RECENT_MANIFESTS_PATH.exists():
        return []
    recent = json.loads(RECENT_MANIFESTS_PATH.read_text(encoding="utf-8"))
    return [path for path in recent if Path(path).exists()]


def save_recent_manifest(manifest_path: Path) -> None:
    ensure_state_dir()
    existing = load_recent_manifests()
    normalized = str(manifest_path)
    updated = [normalized] + [item for item in existing if item != normalized]
    RECENT_MANIFESTS_PATH.write_text(
        json.dumps(updated[:20], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
