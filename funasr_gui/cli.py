from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core.diagnostics import collect_environment_diagnostics
from .core.models import JobManifest, JobSettings, build_file_jobs, discover_media_files
from .core.storage import load_manifest, save_manifest, save_recent_manifest
from .core.transcriber import BatchTranscriber


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="funasr-batch-studio")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a batch transcription job")
    run_parser.add_argument("--input", nargs="+", required=True, help="Input files or folders")
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    run_parser.add_argument("--model", default="paraformer-zh")
    run_parser.add_argument("--vad-model", default="fsmn-vad")
    run_parser.add_argument("--punc-model", default="ct-punc-c")
    run_parser.add_argument("--device", default="cpu")
    run_parser.add_argument("--batch-size-s", type=int, default=300)
    run_parser.add_argument("--hotword-file")
    run_parser.add_argument("--skip-existing", action="store_true")
    run_parser.add_argument("--overwrite-existing", action="store_true")
    run_parser.add_argument("--keep-wav", action="store_true")
    run_parser.add_argument("--no-json", action="store_true")

    manifest_parser = subparsers.add_parser("resume", help="Resume an existing manifest")
    manifest_parser.add_argument("--manifest", required=True)

    diag_parser = subparsers.add_parser("diagnostics", help="Print environment diagnostics")
    diag_parser.add_argument("--ffmpeg-bin", default="ffmpeg")
    return parser


def run_from_args(args: argparse.Namespace) -> int:
    hotwords: list[str] = []
    if args.hotword_file:
        hotwords = [line.strip() for line in Path(args.hotword_file).read_text(encoding="utf-8").splitlines() if line.strip()]

    settings = JobSettings(
        input_paths=args.input,
        output_dir=args.output_dir,
        ffmpeg_bin=args.ffmpeg_bin,
        model=args.model,
        vad_model=args.vad_model,
        punc_model=args.punc_model,
        device=args.device,
        batch_size_s=args.batch_size_s,
        hotwords=hotwords,
        skip_existing=args.skip_existing,
        overwrite_existing=args.overwrite_existing,
        keep_wav=args.keep_wav,
        output_json=not args.no_json,
        output_txt=True,
    )
    files = discover_media_files(settings.input_paths)
    if not files:
        raise SystemExit("No supported input files found.")

    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.cli.json"
    manifest = JobManifest.build(settings, build_file_jobs(files, output_dir))
    save_manifest(manifest_path, manifest)
    save_recent_manifest(manifest_path)
    BatchTranscriber(manifest, manifest_path).process()
    return 0


def resume_manifest(manifest_path: str) -> int:
    manifest_file = Path(manifest_path)
    manifest = load_manifest(manifest_file)
    BatchTranscriber(manifest, manifest_file).process()
    return 0


def print_diagnostics(ffmpeg_bin: str) -> int:
    payload = [item.__dict__ for item in collect_environment_diagnostics(ffmpeg_bin)]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run":
        return run_from_args(args)
    if args.command == "resume":
        return resume_manifest(args.manifest)
    if args.command == "diagnostics":
        return print_diagnostics(args.ffmpeg_bin)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
