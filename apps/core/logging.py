"""
apps/core/logging.py

Intercepts Django's standard `logging` module and routes every log record
through loguru.

Sinks
-----
  stderr          — colourised, all levels (console)
  logs/app.log    — all levels, rotates at 10 MB, retains 7 days, compressed
  logs/error.log  — ERROR and above only, rotates at 10 MB, retains 30 days

Usage
-----
Called once in base.py:

    from pathlib import Path
    from apps.core.logging import setup_loguru

    setup_loguru(log_level=LOG_LEVEL, base_dir=BASE_DIR)

Both styles then work transparently:

    import logging                        # existing Django / third-party code
    logger = logging.getLogger(__name__)
    logger.warning("something happened")

    from loguru import logger             # new app code
    logger.info("user logged in")
"""

import logging
import sys
from pathlib import Path
from loguru import logger


class _InterceptHandler(logging.Handler):
    """Redirect every stdlib logging record into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 0
        while frame and (frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Plain format for file sinks (no colour codes)
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} — "
    "{message}"
)

# Colourised format for console
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
    "<level>{message}</level>"
)


def setup_loguru(log_level: str = "DEBUG", base_dir: Path | None = None) -> None:
    """
    Configure loguru sinks and install the stdlib intercept handler.

    Args:
        log_level : Minimum level to capture. Controlled via LOG_LEVEL in .env.
        base_dir  : Project root (BASE_DIR from settings). Logs are written to
                    <base_dir>/logs/. Defaults to current working directory.
    """
    logs_dir = (base_dir or Path.cwd()) / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Remove loguru's default stderr sink
    logger.remove()

    # ── Sink 1: console (colourised) ────────────────────────────────────────
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=_CONSOLE_FORMAT,
        backtrace=True,
        diagnose=True,   # shows variable values — disable in production
    )

    # ── Sink 2: logs/app.log — all levels ───────────────────────────────────
    logger.add(
        logs_dir / "app.log",
        level=log_level,
        format=_FILE_FORMAT,
        rotation="10 MB",       # new file after 10 MB
        retention="7 days",     # delete files older than 7 days
        compression="zip",      # compress rotated files
        backtrace=True,
        diagnose=False,         # never write variable values to disk
        encoding="utf-8",
        enqueue=True,           # thread-safe async writes
    )

    # ── Sink 3: logs/error.log — ERROR and above only ───────────────────────
    logger.add(
        logs_dir / "error.log",
        level="ERROR",
        format=_FILE_FORMAT,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=False,
        encoding="utf-8",
        enqueue=True,
    )

    # ── Intercept stdlib logging ─────────────────────────────────────────────
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    # Quieten noisy third-party loggers at DEBUG
    for noisy in ("django", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.INFO)

    logger.info("Loguru configured — logs directory: {}", logs_dir)
