from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from funasr_gui.gui.main_window import MainWindow


class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_window_builds_and_detects_inputs(self) -> None:
        window = MainWindow()
        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir) / "clip.mp4"
            media_path.write_text("x", encoding="utf-8")
            window._append_input_item(str(media_path))
            window._refresh_input_summary()
            self.assertIn("1 supported files", window.input_summary.text())
            window.preset_combo.setCurrentText("Fast CPU")
            window._apply_selected_preset()
            self.assertEqual(window.batch_spin.value(), 120)
        window.close()


if __name__ == "__main__":
    unittest.main()
