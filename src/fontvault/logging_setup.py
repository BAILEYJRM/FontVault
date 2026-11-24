"""Rotating file logging, Qt message capture, and native crash diagnostics."""

from __future__ import annotations

import faulthandler
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

from fontvault.config import AppPaths


_FAULTHANDLER_STREAM: TextIO | None = None
_QT_HANDLER_INSTALLED = False


def setup_logging(paths: AppPaths, level: int = logging.INFO) -> Path:
    """Configure rotating file logging, exception hooks, and native faulthandler."""
    global _FAULTHANDLER_STREAM
    paths.ensure_dirs()
    log_file = paths.logs_dir / "fontvault.log"
    crash_file = paths.logs_dir / "crash_faulthandler.log"

    pkg_logger = logging.getLogger("fontvault")
    pkg_logger.setLevel(level)
    pkg_logger.propagate = False

    # Replace existing file handlers if setup_logging is invoked again (e.g. in tests).
    for handler in list(pkg_logger.handlers):
        pkg_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(threadName)s): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    pkg_logger.addHandler(file_handler)

    try:
        if _FAULTHANDLER_STREAM is not None:
            try:
                faulthandler.disable()
            except Exception:
                pass
            try:
                _FAULTHANDLER_STREAM.close()
            except Exception:
                pass
        _FAULTHANDLER_STREAM = crash_file.open("a", encoding="utf-8")
        faulthandler.enable(file=_FAULTHANDLER_STREAM, all_threads=True)
    except Exception as exc:
        pkg_logger.warning("No se pudo habilitar faulthandler: %s", exc)

    def _sys_excepthook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        pkg_logger.critical(
            "Excepción no controlada en hilo principal",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
        pkg_logger.critical(
            "Excepción no controlada en hilo '%s'",
            getattr(args.thread, "name", "desconocido"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _sys_excepthook
    threading.excepthook = _thread_excepthook
    return log_file


def install_qt_message_handler() -> None:
    """Forward Qt warnings, criticals, and fatals into fontvault.qt logger."""
    global _QT_HANDLER_INSTALLED
    if _QT_HANDLER_INSTALLED:
        return

    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    qt_logger = logging.getLogger("fontvault.qt")

    def _qt_handler(msg_type: QtMsgType, _context, message: str) -> None:
        if msg_type == QtMsgType.QtDebugMsg:
            qt_logger.debug("%s", message)
        elif msg_type == QtMsgType.QtInfoMsg:
            qt_logger.info("%s", message)
        elif msg_type == QtMsgType.QtWarningMsg:
            qt_logger.warning("%s", message)
        elif msg_type == QtMsgType.QtCriticalMsg:
            qt_logger.error("%s", message)
        elif msg_type == QtMsgType.QtFatalMsg:
            qt_logger.critical("QT FATAL: %s", message)

    qInstallMessageHandler(_qt_handler)
    _QT_HANDLER_INSTALLED = True
