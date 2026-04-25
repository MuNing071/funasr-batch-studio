# Agent Handoff

This document is the operational handoff for future agents working on `funasr-batch-studio`.

## 1. Project identity

- Project name: `funasr-batch-studio`
- Repo root: `G:\FunASR\funasr-batch-studio`
- GitHub repo: `https://github.com/MuNing071/funasr-batch-studio`
- Default branch: `main`
- Current maturity: alpha, but already validated on real long-video transcription workflows

This repo is intentionally separate from the upstream FunASR source tree. Do not fold upstream source code into this repo unless there is a very explicit redistribution decision.

## 2. Mission

The product goal is to turn local long-form transcription with FunASR into a usable desktop workflow:

- batch-select files or folders
- configure models and runtime behavior
- add hotwords
- run long jobs safely
- resume, retry, inspect failures
- package it into something open-source contributors can understand and extend

## 3. Current architecture

The app is split into a thin UI shell and a small core.

### 3.1 Entry points

- `launch_funasr_gui.py`
  - convenience launcher for local development
- `funasr_gui/app.py`
  - GUI entry point
- `funasr_gui/cli.py`
  - headless utility entry point for diagnostics and batch execution

### 3.2 Core layer

#### `funasr_gui/core/models.py`

Defines data models and file discovery helpers.

Main types:

- `JobSettings`
- `FileJob`
- `JobManifest`

Important notes:

- `JobSettings` is the main config contract shared across GUI, CLI, persistence, and runtime
- `discover_media_files()` currently scans only one folder level for directory inputs
- `build_file_jobs()` creates one txt/json pair per input file

#### `funasr_gui/core/storage.py`

Owns persistence for:

- app settings
- vocabulary presets
- recent manifest list
- manifest save/load

Important notes:

- app state is stored outside the repo by default
- environment override: `FUNASR_BATCH_STUDIO_HOME`
- storage is JSON-based and human-inspectable

#### `funasr_gui/core/paths.py`

Owns path resolution rules:

- `PROJECT_ROOT`
- default ffmpeg discovery
- user app-state directory selection

Important notes:

- this module is what keeps the repo portable
- if more filesystem policies appear, they should land here first

#### `funasr_gui/core/presets.py`

Contains curated model presets.

Current use:

- the GUI preset selector

Future use:

- CLI preset shortcuts
- user-editable preset files if product scope expands

#### `funasr_gui/core/diagnostics.py`

Performs local dependency and capability checks.

Current checks:

- Python
- `funasr`
- `torchaudio`
- `PySide6`
- `ffmpeg`
- `cuda`

This module should stay read-only and side-effect free.

#### `funasr_gui/core/transcriber.py`

This is the actual runtime pipeline.

Responsibilities:

- create output and temp dirs
- load the FunASR model lazily
- extract wav via `ffmpeg` when needed
- invoke `AutoModel.generate`
- post-process text
- write `.txt` and optional `.json`
- update manifest state after each transition

Design assumptions:

- processing is sequential
- pause means "pause before the next file", not "interrupt current inference"
- manifest is the recovery truth

Known constraints:

- no per-chunk progress from FunASR yet
- no subtitle export yet
- no explicit download manager for first-time model pulls

#### `funasr_gui/core/worker.py`

Qt bridge between background processing and the UI.

Responsibilities:

- run `BatchTranscriber` in a worker thread
- surface lifecycle and file update signals back to the main window

### 3.3 GUI layer

#### `funasr_gui/gui/main_window.py`

This is the only UI screen today.

Main UI zones:

- input selection
- setup tabs
  - Models
  - History
  - Diagnostics
- hotword editor
- output and run controls
- queue table
- logs

Responsibilities:

- collect form values into `JobSettings`
- create and load manifests
- manage worker lifecycle
- update queue state and logs
- keep diagnostics and recent history visible

Product behaviors already implemented:

- start new job
- pause
- resume
- stop after current file
- retry failed
- open old manifest
- resume pending
- export logs
- open output folder

## 4. Runtime flow

For a new GUI batch:

1. user selects files or folders
2. GUI normalizes the form into `JobSettings`
3. `discover_media_files()` resolves supported inputs
4. a fresh `JobManifest` is created
5. manifest is saved to `manifest.gui.json`
6. GUI launches `TranscriptionWorker` in a `QThread`
7. `BatchTranscriber.process()` walks files sequentially
8. each file moves through states such as:
   - `Pending`
   - `Extracting Audio`
   - `Transcribing`
   - `Writing Output`
   - `Success` / `Failed` / `Skipped`
9. outputs are written to the chosen output directory
10. manifest is updated after every state change
11. GUI refreshes the table, logs, and summary metrics from worker signals

## 5. File and state contracts

### 5.1 Output files

Per media file:

- `<name>.txt`
- `<name>.json` when enabled

Per job:

- `manifest.gui.json`

Temp:

- `_wav_tmp/<md5>.wav`

### 5.2 App state files

Default app-state dir:

- `%APPDATA%\FunASRBatchStudio` on Windows
- `~/.funasr_batch_studio` elsewhere

Files:

- `settings.json`
- `vocabulary_presets.json`
- `recent_manifests.json`

### 5.3 Manifest semantics

Important behaviors:

- existing successful txt output can trigger skip
- `[ERROR]` prefix is treated as failed output on rerun logic
- recent manifest list is used as the "History" UX source

Manifest compatibility matters. If fields change:

- prefer additive changes
- keep sensible defaults in deserialization
- update tests and docs in the same change

## 6. Testing status

Current automated tests live in:

- `tests/test_core.py`
- `tests/test_gui_smoke.py`

Currently covered:

- media discovery
- output path generation
- manifest roundtrip
- settings and recent manifest storage
- diagnostics coverage
- CLI parser construction
- GUI window initialization
- preset application smoke

Manual validation already done:

- real end-to-end transcription on a local sample wav
- GUI offscreen startup
- CLI diagnostics run

## 7. Known gaps

These are the most important missing pieces for the next agent.

### Product gaps

- no multi-page UI or deeper job detail view
- no packaged installer
- no first-run setup assistant
- no model cache management UX
- no subtitle export
- no transcript preview/editor in-app

### Engineering gaps

- no integration tests with mocked FunASR runtime objects
- no manifest schema version field yet
- no structured logging abstraction yet
- no dedicated service layer between UI and manifest orchestration

### Release gaps

- no screenshots in README yet
- no GitHub Releases yet
- no signed binaries or installer artifacts
- no dependency pinning strategy beyond broad version ranges

## 8. Recommended next priorities

If continuing immediately, do the work in roughly this order:

1. Add subtitle export:
   - `srt`
   - `vtt`
2. Add manifest versioning and migration helpers
3. Add a transcript preview pane and per-file open action
4. Add better end-to-end tests around retry/resume
5. Add packaging:
   - PyInstaller or similar
   - app icon
   - release artifact workflow
6. Add README screenshots and a short demo GIF

## 9. Working rules for future agents

- Keep UI code in `gui/` and processing logic in `core/`
- Avoid hardcoding machine-local absolute paths
- Do not couple new features directly to `main_window.py` if they can live in core
- Preserve JSON manifest readability
- Prefer additive schema evolution
- Run tests after touching persistence, entry points, or UI startup
- If changing release-facing behavior, update:
  - `README.md`
  - `CHANGELOG.md`
  - `docs/ARCHITECTURE.md` when needed

## 10. Useful commands

### Run GUI

```powershell
python launch_funasr_gui.py
```

### Run tests

```powershell
$env:PYTHONPATH='.'
python -m unittest discover -s tests -v
```

### Run diagnostics

```powershell
$env:PYTHONPATH='.'
python -m funasr_gui.cli diagnostics
```

### Resume a manifest from CLI

```powershell
$env:PYTHONPATH='.'
python -m funasr_gui.cli resume --manifest <path-to-manifest>
```

## 11. Git state at handoff

At the time this document was written:

- repo is initialized
- branch is `main`
- GitHub remote is configured
- initial alpha commits are already pushed

If the next agent starts from a dirty worktree, inspect carefully before editing. This repo is now public-facing, so release hygiene matters.
