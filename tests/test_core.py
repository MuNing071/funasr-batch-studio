from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from funasr_gui.cli import build_parser
from funasr_gui.core.diagnostics import collect_environment_diagnostics
from funasr_gui.core.models import JobManifest, JobSettings, build_file_jobs, discover_media_files
from funasr_gui.core.storage import (
    load_manifest,
    load_recent_manifests,
    load_settings,
    save_manifest,
    save_recent_manifest,
    save_settings,
)


class CoreTests(unittest.TestCase):
    def test_discover_media_files_deduplicates_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "a.mp4").write_text("x", encoding="utf-8")
            (temp_path / "b.txt").write_text("x", encoding="utf-8")
            files = discover_media_files([str(temp_path), str(temp_path / "a.mp4")])
            self.assertEqual([item.name for item in files], ["a.mp4"])

    def test_build_file_jobs_creates_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "transcripts"
            jobs = build_file_jobs([Path(temp_dir) / "demo.mp4"], output_dir)
            self.assertEqual(jobs[0].output_txt_path, str(output_dir / "demo.txt"))
            self.assertEqual(jobs[0].output_json_path, str(output_dir / "demo.json"))

    def test_manifest_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings = JobSettings(input_paths=["a.mp4"], output_dir=str(temp_path))
            manifest = JobManifest.build(settings, build_file_jobs([temp_path / "a.mp4"], temp_path))
            manifest_path = temp_path / "manifest.json"
            save_manifest(manifest_path, manifest)
            loaded = load_manifest(manifest_path)
            self.assertEqual(loaded.settings.output_dir, str(temp_path))
            self.assertEqual(len(loaded.files), 1)

    def test_settings_and_recent_manifest_storage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            settings_path = temp_path / "settings.json"
            vocab_path = temp_path / "vocab.json"
            recent_path = temp_path / "recent.json"
            with (
                patch("funasr_gui.core.storage.APP_STATE_DIR", temp_path),
                patch("funasr_gui.core.storage.SETTINGS_PATH", settings_path),
                patch("funasr_gui.core.storage.VOCAB_PRESETS_PATH", vocab_path),
                patch("funasr_gui.core.storage.RECENT_MANIFESTS_PATH", recent_path),
            ):
                settings = JobSettings(input_paths=["x.mp4"], output_dir=str(temp_path), ffmpeg_bin="ffmpeg")
                save_settings(settings)
                loaded = load_settings()
                self.assertEqual(loaded.output_dir, str(temp_path))

                manifest_file = temp_path / "manifest.gui.json"
                manifest_file.write_text("{}", encoding="utf-8")
                save_recent_manifest(manifest_file)
                self.assertEqual(load_recent_manifests(), [str(manifest_file)])

    def test_diagnostics_returns_expected_sections(self) -> None:
        items = collect_environment_diagnostics("ffmpeg")
        names = {item.name for item in items}
        self.assertTrue({"python", "funasr", "torchaudio", "PySide6", "ffmpeg", "cuda"}.issubset(names))

    def test_cli_parser_builds_run_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["diagnostics"])
        self.assertEqual(args.command, "diagnostics")


if __name__ == "__main__":
    unittest.main()
