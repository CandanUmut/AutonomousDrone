from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LinkStatus:
    connected: bool
    rssi_dbm: float | None = None


def get_link_status() -> LinkStatus:
    logger.info("Link status stub")
    return LinkStatus(connected=True, rssi_dbm=-50.0)
