from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox

from timesync_sim.ca_engine import CAEngine
from timesync_sim.config import ConfigurationError, load_ca_configuration
from timesync_sim.gui.ca_window import CAWindow
from timesync_sim.gui.common import choose_json_configuration


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Time Sync CA Simulator")

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    if config_path is None:
        config_path = choose_json_configuration(
            None,
            "Select a CA node configuration",
            str(PROJECT_ROOT / "configs"),
        )
    if not config_path:
        return 0

    try:
        config, topology, _ = load_ca_configuration(config_path)
        engine = CAEngine(config, topology)
    except (ConfigurationError, RuntimeError) as exc:
        QMessageBox.critical(None, "CA startup failed", str(exc))
        return 1

    window = CAWindow(engine)
    window.show()
    engine.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
