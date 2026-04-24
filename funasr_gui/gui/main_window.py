from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.diagnostics import collect_environment_diagnostics
from ..core.models import JobManifest, JobSettings, build_file_jobs, discover_media_files
from ..core.presets import MODEL_PRESETS
from ..core.storage import (
    load_manifest,
    load_recent_manifests,
    load_settings,
    load_vocab_presets,
    save_manifest,
    save_recent_manifest,
    save_settings,
    save_vocab_presets,
)
from ..core.worker import TranscriptionWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FunASR Batch Studio")
        self.resize(1460, 940)

        self.settings = load_settings()
        self.vocab_presets = load_vocab_presets()
        self.recent_manifests = load_recent_manifests()
        self.manifest: JobManifest | None = None
        self.manifest_path: Path | None = None
        self.worker_thread: QThread | None = None
        self.worker: TranscriptionWorker | None = None
        self.row_by_source: dict[str, int] = {}

        self._build_ui()
        self._load_settings_into_form(self.settings)
        self._refresh_vocab_presets()
        self._refresh_history()
        self._refresh_diagnostics()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QGridLayout(root)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)

        left_panel = QVBoxLayout()
        right_panel = QVBoxLayout()
        layout.addLayout(left_panel, 0, 0)
        layout.addLayout(right_panel, 0, 1)

        left_panel.addWidget(self._build_input_group())
        left_panel.addWidget(self._build_setup_tabs())
        left_panel.addWidget(self._build_hotword_group())
        left_panel.addWidget(self._build_output_group())
        left_panel.addStretch(1)

        right_panel.addWidget(self._build_job_group())
        right_panel.addWidget(self._build_log_group())

    def _build_input_group(self) -> QGroupBox:
        group = QGroupBox("Input")
        layout = QVBoxLayout(group)

        self.input_list = QListWidget()
        layout.addWidget(self.input_list)

        buttons = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files")
        self.add_folder_button = QPushButton("Add Folder")
        self.remove_selected_button = QPushButton("Remove Selected")
        self.clear_inputs_button = QPushButton("Clear")
        buttons.addWidget(self.add_files_button)
        buttons.addWidget(self.add_folder_button)
        buttons.addWidget(self.remove_selected_button)
        buttons.addWidget(self.clear_inputs_button)
        layout.addLayout(buttons)

        self.input_summary = QLabel("No files selected")
        layout.addWidget(self.input_summary)

        self.add_files_button.clicked.connect(self._select_files)
        self.add_folder_button.clicked.connect(self._select_folder)
        self.remove_selected_button.clicked.connect(self._remove_selected_inputs)
        self.clear_inputs_button.clicked.connect(self._clear_inputs)
        return group

    def _build_setup_tabs(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_model_group(), "Models")
        tabs.addTab(self._build_history_group(), "History")
        tabs.addTab(self._build_diagnostics_group(), "Diagnostics")
        return tabs

    def _build_model_group(self) -> QGroupBox:
        group = QGroupBox("Model Settings")
        form = QFormLayout(group)

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(MODEL_PRESETS.keys())
        self.apply_preset_button = QPushButton("Apply")
        self.preset_description = QLabel("")
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.apply_preset_button)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["paraformer-zh", "SenseVoiceSmall"])
        self.vad_combo = QComboBox()
        self.vad_combo.addItems(["fsmn-vad", "none"])
        self.punc_combo = QComboBox()
        self.punc_combo.addItems(["ct-punc-c", "none"])
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda"])
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(10, 3600)
        self.batch_spin.setSingleStep(10)
        self.ffmpeg_edit = QLineEdit()
        self.ffmpeg_browse_button = QPushButton("Browse")
        ffmpeg_layout = QHBoxLayout()
        ffmpeg_layout.addWidget(self.ffmpeg_edit)
        ffmpeg_layout.addWidget(self.ffmpeg_browse_button)

        form.addRow("Preset", preset_layout)
        form.addRow("", self.preset_description)
        form.addRow("ASR Model", self.model_combo)
        form.addRow("VAD Model", self.vad_combo)
        form.addRow("Punctuation", self.punc_combo)
        form.addRow("Device", self.device_combo)
        form.addRow("Batch Size (s)", self.batch_spin)
        form.addRow("ffmpeg", ffmpeg_layout)

        self.apply_preset_button.clicked.connect(self._apply_selected_preset)
        self.preset_combo.currentTextChanged.connect(self._update_preset_description)
        self.ffmpeg_browse_button.clicked.connect(self._choose_ffmpeg)
        return group

    def _build_history_group(self) -> QGroupBox:
        group = QGroupBox("Recent Jobs")
        layout = QVBoxLayout(group)
        self.history_list = QListWidget()
        self.history_open_button = QPushButton("Open Selected Manifest")
        self.history_refresh_button = QPushButton("Refresh")
        buttons = QHBoxLayout()
        buttons.addWidget(self.history_open_button)
        buttons.addWidget(self.history_refresh_button)
        layout.addWidget(self.history_list)
        layout.addLayout(buttons)
        self.history_open_button.clicked.connect(self._open_selected_history_manifest)
        self.history_refresh_button.clicked.connect(self._refresh_history)
        return group

    def _build_diagnostics_group(self) -> QGroupBox:
        group = QGroupBox("Environment")
        layout = QVBoxLayout(group)
        self.diagnostics_text = QPlainTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.refresh_diagnostics_button = QPushButton("Refresh Diagnostics")
        layout.addWidget(self.diagnostics_text)
        layout.addWidget(self.refresh_diagnostics_button)
        self.refresh_diagnostics_button.clicked.connect(self._refresh_diagnostics)
        return group

    def _build_hotword_group(self) -> QGroupBox:
        group = QGroupBox("Hotwords / Vocabulary")
        layout = QVBoxLayout(group)

        preset_row = QHBoxLayout()
        self.vocab_preset_combo = QComboBox()
        self.load_preset_button = QPushButton("Load Preset")
        self.save_preset_button = QPushButton("Save Preset")
        preset_row.addWidget(self.vocab_preset_combo)
        preset_row.addWidget(self.load_preset_button)
        preset_row.addWidget(self.save_preset_button)
        layout.addLayout(preset_row)

        self.hotwords_edit = QTextEdit()
        self.hotwords_edit.setPlaceholderText("One hotword per line")
        layout.addWidget(self.hotwords_edit)

        self.load_preset_button.clicked.connect(self._load_vocab_preset)
        self.save_preset_button.clicked.connect(self._save_vocab_preset)
        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("Output")
        form = QFormLayout(group)

        self.output_dir_edit = QLineEdit()
        self.output_browse_button = QPushButton("Browse")
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(self.output_browse_button)

        self.skip_existing_checkbox = QCheckBox("Skip existing successful transcripts")
        self.overwrite_checkbox = QCheckBox("Overwrite existing output")
        self.keep_wav_checkbox = QCheckBox("Keep temp wav files")
        self.output_txt_checkbox = QCheckBox("Write txt output")
        self.output_json_checkbox = QCheckBox("Write json output")
        self.open_output_checkbox = QCheckBox("Open output folder when finished")

        form.addRow("Output Folder", output_layout)
        form.addRow("", self.skip_existing_checkbox)
        form.addRow("", self.overwrite_checkbox)
        form.addRow("", self.keep_wav_checkbox)
        form.addRow("", self.output_txt_checkbox)
        form.addRow("", self.output_json_checkbox)
        form.addRow("", self.open_output_checkbox)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.resume_pending_button = QPushButton("Resume Pending")
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.stop_button = QPushButton("Stop")
        self.retry_failed_button = QPushButton("Retry Failed")
        self.open_output_button = QPushButton("Open Output")
        self.export_log_button = QPushButton("Export Log")
        controls.addWidget(self.start_button)
        controls.addWidget(self.resume_pending_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.resume_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.retry_failed_button)
        controls.addWidget(self.open_output_button)
        controls.addWidget(self.export_log_button)
        form.addRow("", controls)

        self.output_browse_button.clicked.connect(self._choose_output_dir)
        self.start_button.clicked.connect(self._start_job)
        self.resume_pending_button.clicked.connect(self._resume_pending)
        self.pause_button.clicked.connect(self._pause_job)
        self.resume_button.clicked.connect(self._resume_job)
        self.stop_button.clicked.connect(self._stop_job)
        self.retry_failed_button.clicked.connect(self._retry_failed)
        self.open_output_button.clicked.connect(self._open_output_folder)
        self.export_log_button.clicked.connect(self._export_logs)
        return group

    def _build_job_group(self) -> QGroupBox:
        group = QGroupBox("Queue")
        layout = QVBoxLayout(group)

        metrics = QHBoxLayout()
        self.global_progress = QProgressBar()
        self.global_progress.setRange(0, 100)
        self.status_label = QLabel("Idle")
        self.summary_label = QLabel("0 files")
        self.current_file_label = QLabel("Current: -")
        self.eta_label = QLabel("ETA: -")
        self.open_manifest_button = QPushButton("Open Manifest")
        metrics.addWidget(self.global_progress, 1)
        metrics.addWidget(self.status_label)
        metrics.addWidget(self.summary_label)
        metrics.addWidget(self.current_file_label)
        metrics.addWidget(self.eta_label)
        metrics.addWidget(self.open_manifest_button)
        layout.addLayout(metrics)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["File", "State", "Progress", "Chars", "Error"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.open_manifest_button.clicked.connect(self._open_manifest)
        self._set_run_controls(is_running=False)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("Logs")
        layout = QVBoxLayout(group)
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)
        return group

    def _load_settings_into_form(self, settings: JobSettings) -> None:
        self.input_list.clear()
        self.ffmpeg_edit.setText(settings.ffmpeg_bin)
        self.output_dir_edit.setText(settings.output_dir)
        self.batch_spin.setValue(settings.batch_size_s)
        self._set_combo_value(self.preset_combo, settings.preset_name or "Balanced")
        self._set_combo_value(self.model_combo, settings.model)
        self._set_combo_value(self.vad_combo, settings.vad_model or "none")
        self._set_combo_value(self.punc_combo, settings.punc_model or "none")
        self._set_combo_value(self.device_combo, settings.device)
        self.skip_existing_checkbox.setChecked(settings.skip_existing)
        self.overwrite_checkbox.setChecked(settings.overwrite_existing)
        self.keep_wav_checkbox.setChecked(settings.keep_wav)
        self.output_json_checkbox.setChecked(settings.output_json)
        self.output_txt_checkbox.setChecked(settings.output_txt)
        self.open_output_checkbox.setChecked(settings.open_output_when_done)
        self.hotwords_edit.setPlainText("\n".join(settings.hotwords))
        for item in settings.input_paths:
            self._append_input_item(item)
        self._update_preset_description(self.preset_combo.currentText())
        self._refresh_input_summary()

    def _collect_settings(self) -> JobSettings:
        settings = JobSettings(
            input_paths=[self.input_list.item(i).text() for i in range(self.input_list.count())],
            output_dir=self.output_dir_edit.text().strip(),
            ffmpeg_bin=self.ffmpeg_edit.text().strip(),
            preset_name=self.preset_combo.currentText(),
            model=self.model_combo.currentText(),
            vad_model="" if self.vad_combo.currentText() == "none" else self.vad_combo.currentText(),
            punc_model="" if self.punc_combo.currentText() == "none" else self.punc_combo.currentText(),
            device=self.device_combo.currentText(),
            batch_size_s=self.batch_spin.value(),
            hotwords=self._normalized_hotwords(),
            skip_existing=self.skip_existing_checkbox.isChecked(),
            overwrite_existing=self.overwrite_checkbox.isChecked(),
            keep_wav=self.keep_wav_checkbox.isChecked(),
            output_json=self.output_json_checkbox.isChecked(),
            output_txt=self.output_txt_checkbox.isChecked(),
            open_output_when_done=self.open_output_checkbox.isChecked(),
        )
        save_settings(settings)
        self.settings = settings
        return settings

    def _start_job(self) -> None:
        settings = self._collect_settings()
        files = discover_media_files(settings.input_paths)
        if not files:
            QMessageBox.warning(self, "No Files", "Please select at least one supported media file.")
            return
        if not settings.output_dir:
            default_output = str(Path(files[0]).parent / "transcripts")
            self.output_dir_edit.setText(default_output)
            settings.output_dir = default_output
            save_settings(settings)

        output_dir = Path(settings.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = output_dir / "manifest.gui.json"
        self.manifest = JobManifest.build(settings, build_file_jobs(files, output_dir))
        save_manifest(self.manifest_path, self.manifest)
        save_recent_manifest(self.manifest_path)
        self._refresh_history()
        self._populate_table()
        self._append_log(f"Job created with {len(files)} files")
        self._launch_worker()

    def _retry_failed(self) -> None:
        if self.manifest_path is None or not self.manifest_path.exists():
            output_dir = self.output_dir_edit.text().strip()
            candidate = Path(output_dir) / "manifest.gui.json" if output_dir else None
            if candidate is None or not candidate.exists():
                QMessageBox.information(self, "Retry Failed", "No previous job manifest found.")
                return
            self.manifest_path = candidate

        manifest = load_manifest(self.manifest_path)
        manifest.settings = self._collect_settings()
        pending = 0
        for file_job in manifest.files:
            if file_job.state == "Failed":
                file_job.state = "Pending"
                file_job.progress = 0
                file_job.error = ""
                pending += 1
        if pending == 0:
            QMessageBox.information(self, "Retry Failed", "There are no failed files to retry.")
            return
        self.manifest = manifest
        save_manifest(self.manifest_path, self.manifest)
        save_recent_manifest(self.manifest_path)
        self._refresh_history()
        self._populate_table()
        self._append_log(f"Retrying {pending} failed files")
        self._launch_worker()

    def _resume_pending(self) -> None:
        if self.manifest_path is None or not self.manifest_path.exists():
            output_dir = self.output_dir_edit.text().strip()
            candidate = Path(output_dir) / "manifest.gui.json" if output_dir else None
            if candidate is None or not candidate.exists():
                QMessageBox.information(self, "Resume Pending", "No manifest found to resume.")
                return
            self.manifest_path = candidate

        manifest = load_manifest(self.manifest_path)
        manifest.settings = self._collect_settings()
        resumable = 0
        for file_job in manifest.files:
            if file_job.state in {"Pending", "Paused", "Stopped"}:
                file_job.state = "Pending"
                file_job.progress = 0
                file_job.error = ""
                resumable += 1
        if resumable == 0:
            QMessageBox.information(self, "Resume Pending", "There are no pending files to resume.")
            return
        self.manifest = manifest
        save_manifest(self.manifest_path, self.manifest)
        save_recent_manifest(self.manifest_path)
        self._refresh_history()
        self._populate_table()
        self._append_log(f"Resuming {resumable} pending files")
        self._launch_worker()

    def _open_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Manifest", "", "Manifest (*.json)")
        if not path:
            return
        self._load_manifest_from_path(Path(path))

    def _open_selected_history_manifest(self) -> None:
        item = self.history_list.currentItem()
        if item is None:
            return
        manifest_path = Path(item.text())
        if not manifest_path.exists():
            QMessageBox.warning(self, "Missing Manifest", "The selected manifest file no longer exists.")
            self._refresh_history()
            return
        self._load_manifest_from_path(manifest_path)

    def _load_manifest_from_path(self, manifest_path: Path) -> None:
        manifest = load_manifest(manifest_path)
        self.manifest_path = manifest_path
        self.manifest = manifest
        save_recent_manifest(manifest_path)
        self._refresh_history()
        self._apply_manifest_to_form(manifest)
        self._populate_table()
        self._append_log(f"Loaded manifest: {manifest_path}")

    def _launch_worker(self) -> None:
        if self.manifest is None or self.manifest_path is None:
            return
        self._cleanup_worker()
        self.worker_thread = QThread(self)
        self.worker = TranscriptionWorker(self.manifest, self.manifest_path)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.file_updated.connect(self._on_file_updated)
        self.worker.lifecycle.connect(self._on_worker_lifecycle)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self._set_run_controls(is_running=True)
        self.worker_thread.start()

    def _cleanup_worker(self) -> None:
        if self.worker_thread is not None:
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
        self.worker_thread = None
        self.worker = None

    def _pause_job(self) -> None:
        if self.worker is not None:
            self.worker.request_pause()
            self._append_log("Pause requested")

    def _resume_job(self) -> None:
        if self.worker is not None:
            self.worker.request_resume()
            self._append_log("Resume requested")

    def _stop_job(self) -> None:
        if self.worker is not None:
            self.worker.request_stop()
            self._append_log("Stop requested")

    def _on_worker_failed(self, message: str) -> None:
        self._append_log(f"Worker failed: {message}")
        QMessageBox.critical(self, "Worker Failed", message)

    def _on_worker_finished(self) -> None:
        self._append_log("Job finished")
        self._set_run_controls(is_running=False)
        self._refresh_summary()
        if self.manifest and self.manifest.settings.open_output_when_done:
            self._open_output_folder()

    def _on_worker_lifecycle(self, state: str) -> None:
        self.status_label.setText(state.capitalize())

    def _on_file_updated(self, source_path: str, state: str, progress: int, message: str, chars: int) -> None:
        row = self.row_by_source.get(source_path)
        if row is None:
            return
        self.current_file_label.setText(f"Current: {Path(source_path).name}")
        self.table.item(row, 1).setText(state)
        self.table.item(row, 2).setText(f"{progress}%")
        self.table.item(row, 3).setText(str(chars))
        self.table.item(row, 4).setText("" if state != "Failed" else message)
        self._append_log(f"{Path(source_path).name}: {message}")
        self._refresh_summary()

    def _populate_table(self) -> None:
        self.table.setRowCount(0)
        self.row_by_source.clear()
        if self.manifest is None:
            return
        for row, file_job in enumerate(self.manifest.files):
            self.table.insertRow(row)
            values = [
                Path(file_job.source_path).name,
                file_job.state,
                f"{file_job.progress}%",
                str(file_job.chars),
                file_job.error,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)
            self.row_by_source[file_job.source_path] = row
        self._refresh_summary()

    def _apply_manifest_to_form(self, manifest: JobManifest) -> None:
        self._load_settings_into_form(manifest.settings)
        self._refresh_input_summary()

    def _refresh_summary(self) -> None:
        if self.manifest is None:
            self.global_progress.setValue(0)
            self.summary_label.setText("0 files")
            self.current_file_label.setText("Current: -")
            self.eta_label.setText("ETA: -")
            return
        total = len(self.manifest.files)
        finished = sum(1 for item in self.manifest.files if item.state in {"Success", "Failed", "Skipped", "Stopped"})
        success = sum(1 for item in self.manifest.files if item.state == "Success")
        failed = sum(1 for item in self.manifest.files if item.state == "Failed")
        skipped = sum(1 for item in self.manifest.files if item.state == "Skipped")
        progress = int((finished / total) * 100) if total else 0
        self.global_progress.setValue(progress)
        self.summary_label.setText(f"{total} files | {success} success | {failed} failed | {skipped} skipped")

        completed_durations = [item.duration_seconds for item in self.manifest.files if item.duration_seconds]
        remaining = total - finished
        if completed_durations and remaining > 0:
            avg_seconds = sum(completed_durations) / len(completed_durations)
            eta_minutes = max(1, int((avg_seconds * remaining) / 60))
            self.eta_label.setText(f"ETA: ~{eta_minutes} min")
        else:
            self.eta_label.setText("ETA: -")

    def _set_run_controls(self, is_running: bool) -> None:
        self.start_button.setEnabled(not is_running)
        self.resume_pending_button.setEnabled(not is_running)
        self.pause_button.setEnabled(is_running)
        self.resume_button.setEnabled(is_running)
        self.stop_button.setEnabled(is_running)
        self.retry_failed_button.setEnabled(not is_running)
        self.open_manifest_button.setEnabled(not is_running)
        self.history_open_button.setEnabled(not is_running)
        self.open_output_button.setEnabled(True)
        self.export_log_button.setEnabled(True)

    def _append_log(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_edit.appendPlainText(f"[{timestamp}] {text}")

    def _normalized_hotwords(self) -> list[str]:
        return sorted({line.strip() for line in self.hotwords_edit.toPlainText().splitlines() if line.strip()})

    def _refresh_vocab_presets(self) -> None:
        self.vocab_preset_combo.clear()
        self.vocab_preset_combo.addItems(sorted(self.vocab_presets.keys()))

    def _refresh_history(self) -> None:
        self.recent_manifests = load_recent_manifests()
        self.history_list.clear()
        for path in self.recent_manifests:
            self.history_list.addItem(path)

    def _refresh_diagnostics(self) -> None:
        ffmpeg_bin = self.ffmpeg_edit.text().strip() or self.settings.ffmpeg_bin
        lines: list[str] = []
        for item in collect_environment_diagnostics(ffmpeg_bin):
            lines.append(f"{item.name}: {item.status} | {item.detail}")
        self.diagnostics_text.setPlainText("\n".join(lines))

    def _update_preset_description(self, preset_name: str) -> None:
        preset = MODEL_PRESETS.get(preset_name, {})
        self.preset_description.setText(str(preset.get("description", "")))

    def _apply_selected_preset(self) -> None:
        preset = MODEL_PRESETS.get(self.preset_combo.currentText())
        if not preset:
            return
        self._set_combo_value(self.model_combo, str(preset["model"]))
        self._set_combo_value(self.vad_combo, str(preset["vad_model"] or "none"))
        self._set_combo_value(self.punc_combo, str(preset["punc_model"] or "none"))
        self._set_combo_value(self.device_combo, str(preset["device"]))
        self.batch_spin.setValue(int(preset["batch_size_s"]))
        self._update_preset_description(self.preset_combo.currentText())
        self._append_log(f"Applied preset: {self.preset_combo.currentText()}")

    def _load_vocab_preset(self) -> None:
        name = self.vocab_preset_combo.currentText().strip()
        if not name:
            return
        self.hotwords_edit.setPlainText("\n".join(self.vocab_presets.get(name, [])))

    def _save_vocab_preset(self) -> None:
        words = self._normalized_hotwords()
        if not words:
            QMessageBox.information(self, "Empty Preset", "Add at least one hotword first.")
            return
        name, accepted = QInputDialog.getText(self, "Save Preset", "Preset name")
        if not accepted or not name.strip():
            return
        self.vocab_presets[name.strip()] = words
        save_vocab_presets(self.vocab_presets)
        self._refresh_vocab_presets()
        self.vocab_preset_combo.setCurrentText(name.strip())
        self._append_log(f"Saved vocabulary preset: {name.strip()}")

    def _select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Media Files",
            "",
            "Media Files (*.mp4 *.mkv *.mov *.avi *.flv *.webm *.m4v *.wav *.mp3 *.m4a *.flac)",
        )
        for path in files:
            self._append_input_item(path)
        self._refresh_input_summary()

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self._append_input_item(folder)
            if not self.output_dir_edit.text().strip():
                self.output_dir_edit.setText(str(Path(folder) / "transcripts"))
            self._refresh_input_summary()

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_dir_edit.setText(folder)

    def _choose_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select ffmpeg", "", "Executable (*.exe)")
        if path:
            self.ffmpeg_edit.setText(path)
            self._refresh_diagnostics()

    def _remove_selected_inputs(self) -> None:
        for item in self.input_list.selectedItems():
            self.input_list.takeItem(self.input_list.row(item))
        self._refresh_input_summary()

    def _clear_inputs(self) -> None:
        self.input_list.clear()
        self._refresh_input_summary()

    def _append_input_item(self, path: str) -> None:
        existing = {self.input_list.item(i).text() for i in range(self.input_list.count())}
        if path not in existing:
            self.input_list.addItem(QListWidgetItem(path))

    def _refresh_input_summary(self) -> None:
        paths = [self.input_list.item(i).text() for i in range(self.input_list.count())]
        files = discover_media_files(paths)
        self.input_summary.setText(f"{len(paths)} sources | {len(files)} supported files detected")

    def _open_output_folder(self) -> None:
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            return
        path = Path(output_dir)
        if not path.exists():
            QMessageBox.information(self, "Output Folder", "The output folder does not exist yet.")
            return
        if os.name == "nt":
            os.startfile(str(path))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _export_logs(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Logs", "", "Text Files (*.txt)")
        if not path:
            return
        Path(path).write_text(self.log_edit.toPlainText(), encoding="utf-8")
        self._append_log(f"Logs exported to {path}")

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.worker is not None:
            answer = QMessageBox.question(
                self,
                "Close App",
                "A transcription job is still running. Stop after the current file and close?",
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.request_stop()
            if self.worker_thread is not None:
                self.worker_thread.quit()
                self.worker_thread.wait(1000)
        save_settings(self._collect_settings())
        super().closeEvent(event)


def launch() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
