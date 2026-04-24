from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiagnosticItem:
    name: str
    status: str
    detail: str


def _package_status(module_name: str) -> DiagnosticItem:
    available = importlib.util.find_spec(module_name) is not None
    return DiagnosticItem(
        name=module_name,
        status="ok" if available else "missing",
        detail="Installed" if available else "Not installed",
    )


def collect_environment_diagnostics(ffmpeg_bin: str) -> list[DiagnosticItem]:
    items = [
        DiagnosticItem("python", "ok", sys.version.split()[0]),
        _package_status("funasr"),
        _package_status("torchaudio"),
        _package_status("PySide6"),
    ]

    ffmpeg_resolved = shutil.which(ffmpeg_bin) if ffmpeg_bin else None
    if ffmpeg_resolved is None and ffmpeg_bin:
        explicit = Path(ffmpeg_bin)
        if explicit.exists():
            ffmpeg_resolved = str(explicit)
    items.append(
        DiagnosticItem(
            "ffmpeg",
            "ok" if ffmpeg_resolved else "missing",
            ffmpeg_resolved or "Not found",
        )
    )

    torch_spec = importlib.util.find_spec("torch")
    if torch_spec is None:
        items.append(DiagnosticItem("cuda", "unknown", "torch not installed"))
    else:
        import torch

        items.append(
            DiagnosticItem(
                "cuda",
                "ok" if torch.cuda.is_available() else "info",
                "Available" if torch.cuda.is_available() else "CPU only",
            )
        )
    return items

