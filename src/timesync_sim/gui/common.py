from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


def choose_json_configuration(
    parent: Optional[QWidget],
    title: str,
    initial_directory: Optional[str] = None,
) -> Optional[str]:
    directory = initial_directory or str(Path.cwd())
    path, _ = QFileDialog.getOpenFileName(
        parent,
        title,
        directory,
        "JSON configuration (*.json);;All files (*)",
    )
    if not path:
        return None
    answer = QMessageBox.question(
        parent,
        "Confirm configuration",
        f"Use this configuration?\n\n{path}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return None
    return path


def format_optional_number(value: object, decimals: int = 3) -> str:
    if value is None:
        return "Unknown"
    if isinstance(value, (int, float)):
        return f"{float(value):.{decimals}f}"
    return str(value)
