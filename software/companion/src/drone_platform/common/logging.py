from __future__ import annotations

import json
import logging
from pathlib import Path

from drone_platform.common.types import LoggingConfig


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.args:
            payload["args"] = record.args
        return json.dumps(payload)


def setup_logging(config: LoggingConfig) -> logging.Logger:
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "mission.log"

    logger = logging.getLogger()
    logger.setLevel(config.level)

    formatter: logging.Formatter
    if config.json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(config.level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(config.level)

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_banner(message: str, *, logger: logging.Logger | None = None) -> None:
    banner = f"{message}".center(60, "=")
    if logger is None:
        logger = logging.getLogger(__name__)
    logger.info(banner)
