# FunASR Batch Studio

FunASR Batch Studio is a local desktop app for long-form batch transcription on Windows. It wraps `FunASR`, `ffmpeg`, and a job manifest workflow into a GUI that is easier to operate, resume, and debug than a one-off script.

## What it does

- batch processes folders or manually selected files
- handles long video and audio inputs
- supports model, VAD, punctuation, device, and batch-size controls
- supports hotwords and reusable vocabulary presets
- writes `.txt` and optional `.json` output
- keeps a manifest for resume, retry-failed, and history views
- shows diagnostics, job status, logs, ETA, and per-file state

## Current status

This is an alpha-quality desktop tool that has already been used on a real directory of long Chinese videos. It is structured so the app can be published as a standalone open-source project with a clearer release process.

## Quick start

### 1. Install Python dependencies

```powershell
python -m pip install -U pip
python -m pip install PySide6 funasr torch torchaudio
```

### 2. Make sure `ffmpeg` is available

The app tries these in order:

1. `FUNASR_BATCH_STUDIO_HOME` override for app state only
2. `G:\FunASR\bin\ffmpeg.exe` if present in this workspace
3. `ffmpeg` from `PATH`

### 3. Launch the app

```powershell
python launch_funasr_gui.py
```

## Product highlights

### Input

- add multiple files
- add whole folders
- detect supported media automatically

### Models

- preset-driven setup for balanced, fast CPU, and GPU-heavy runs
- direct editing of ASR, VAD, punctuation, device, and batch size

### Vocabulary

- paste hotwords directly
- save and reload presets

### Output

- choose an output folder
- skip existing successful transcripts
- overwrite output when needed
- keep or clean temp wav files
- open output automatically when done

### Operations

- start
- pause after current file
- resume
- stop after current file
- retry failed
- open old manifest and continue unfinished work

## Architecture

The app is split into small layers:

- `funasr_gui/core/models.py`: job settings and manifest models
- `funasr_gui/core/storage.py`: settings, manifests, vocabulary presets, recent job history
- `funasr_gui/core/transcriber.py`: ffmpeg + FunASR pipeline
- `funasr_gui/core/worker.py`: Qt worker bridge
- `funasr_gui/core/diagnostics.py`: local environment checks
- `funasr_gui/core/presets.py`: curated model presets
- `funasr_gui/gui/main_window.py`: desktop UI

More detail is in `docs/ARCHITECTURE.md`.

## Privacy and compliance posture

- local-first by default
- no telemetry
- outputs stay on disk chosen by the user
- model downloads depend on the upstream runtime and may contact external model registries when a model is not cached yet

Before public release, review:

- model source terms
- third-party licenses
- redistribution rules for bundled binaries like `ffmpeg`
- any jurisdiction-specific speech-data handling requirements

## Open-source readiness checklist

Before publishing to GitHub, I recommend you finish these items:

1. choose a project license
2. confirm third-party redistribution posture
3. decide whether to vendor or require `ffmpeg`
4. run end-to-end GUI tests on at least one CUDA machine and one CPU-only machine
5. add screenshots and a changelog for the first release

## Tests

```powershell
$env:PYTHONPATH='.'
python -m unittest discover -s tests -v
```

## Limitations today

- no packaged installer yet
- no subtitle export yet
- no hard interrupt inside the middle of a single file run
- no dedicated model download manager yet
