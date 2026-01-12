from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraInfo:
    name: str
    stream_url: str | None = None


def list_cameras() -> list[CameraInfo]:
    logger.info("Camera discovery stub.")
    return []


def capture_frame(camera: CameraInfo) -> bytes | None:
    logger.info("Capture frame stub for %s", camera.name)
    return None
