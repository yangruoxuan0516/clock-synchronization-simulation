from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox

from timesync_sim.cm_engine import CMEngine
from timesync_sim.config import ConfigurationError, load_cm_configuration
from timesync_sim.gui.cm_window import CMWindow
from timesync_sim.gui.common import choose_json_configuration


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Time Sync CM Simulator")

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    if config_path is None:
        config_path = choose_json_configuration(
            None,
            "Select a CM node configuration",
            str(PROJECT_ROOT / "configs"),
        )
    if not config_path:
        return 0

    try:
        config, topology, _ = load_cm_configuration(config_path)
        engine = CMEngine(config, topology)
    except (ConfigurationError, RuntimeError) as exc:
        QMessageBox.critical(None, "CM startup failed", str(exc))
        return 1

    window = CMWindow(engine)
    window.show()
    engine.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
