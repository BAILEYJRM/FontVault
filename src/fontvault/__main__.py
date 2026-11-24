"""CLI and GUI application entrypoint for FontVault."""

from __future__ import annotations

import argparse
import ctypes
import logging
import platform
import sys

from PySide6.QtCore import qVersion
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from fontvault import __app_name__, __version__
from fontvault.config import get_resource_path, load_settings, resolve_paths
from fontvault.logging_setup import install_qt_message_handler, setup_logging
from fontvault.ui.main_window import MainWindow
from fontvault.ui.theme import get_stylesheet


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fontvault", description="Gestor de tipografías para Windows")
    parser.add_argument(
        "--portable",
        action="store_true",
        default=None,
        help="Ejecutar en modo portable guardando datos junto al ejecutable",
    )
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    return parser.parse_args(argv)


def _set_windows_app_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "FontVault.TypographyManager.1"
        )
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = resolve_paths(portable_override=True if args.portable else None)
    log_file = setup_logging(paths)
    logger = logging.getLogger("fontvault.app")
    logger.info(
        "Iniciando %s v%s | portable=%s | python=%s | qt=%s | root=%s",
        __app_name__,
        __version__,
        paths.is_portable,
        platform.python_version(),
        qVersion(),
        paths.root_dir,
    )
    settings = load_settings(paths)

    _set_windows_app_id()
    app = QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    install_qt_message_handler()
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setStyleSheet(get_stylesheet(settings.theme))

    icon_path = get_resource_path("assets/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(paths)
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    exit_code = app.exec()
    logger.info("Cierre de %s con código=%s (log=%s)", __app_name__, exit_code, log_file)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
