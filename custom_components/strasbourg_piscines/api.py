"""Client for Strasbourg's public live pool-occupancy dataset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from typing import Any

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import API_URL

_LOGGER = logging.getLogger(__name__)


class StrasbourgPiscinesApiError(Exception):
    """Raised when the public Strasbourg pool feed cannot be used."""


@dataclass(frozen=True, slots=True)
class StrasbourgPiscinesResult:
    """Normalized source response and retrieval time."""

    pools: dict[str, dict[str, Any]]
    fetched_at: datetime


class StrasbourgPiscinesApiClient:
    """Read the public real-time municipal pool feed."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the client with Home Assistant's shared HTTP session."""
        self._session = async_get_clientsession(hass)

    async def async_get_pools(self) -> StrasbourgPiscinesResult:
        """Return every published pool indexed by its stable source identifier."""
        try:
            async with async_timeout.timeout(15):
                async with self._session.get(API_URL) as response:
                    response.raise_for_status()
                    payload = await response.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise StrasbourgPiscinesApiError(
                "Unable to retrieve Strasbourg pool data"
            ) from err

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise StrasbourgPiscinesApiError("Unexpected Strasbourg pool response")

        pools: dict[str, dict[str, Any]] = {}
        for record in results:
            pool = _normalize_pool(record)
            if pool is not None:
                pools[pool["id"]] = pool

        if not pools:
            raise StrasbourgPiscinesApiError("No pool records in Strasbourg response")

        return StrasbourgPiscinesResult(pools, dt_util.utcnow())


def _normalize_pool(record: Any) -> dict[str, Any] | None:
    """Normalize one source record without inferring missing source values."""
    if not isinstance(record, dict):
        return None

    name = record.get("name")
    identifier = record.get("sigid")
    if not isinstance(name, str) or not name or identifier is None:
        _LOGGER.debug("Skipping incomplete Strasbourg pool record: %s", record)
        return None

    is_open = _as_open_state(record.get("isopen"))
    return {
        "id": str(identifier),
        "name": name,
        "is_open": is_open,
        "realtime_status": _as_nonempty_string(record.get("realtimestatus")),
        "occupation": _as_int(record.get("occupation")),
        "today_schedule": _normalize_schedule(record.get("dayschedule")),
        "source_updated_at": _as_nonempty_string(record.get("updatedate")),
        "types": _as_nonempty_string(record.get("types")),
    }


def _as_open_state(value: Any) -> bool | None:
    """Return only a documented 0/1 open state."""
    if value in (1, "1", True):
        return True
    if value in (0, "0", False):
        return False
    return None


def _normalize_schedule(value: Any) -> list[dict[str, int]]:
    """Parse the source's JSON schedule while preserving its individual slots."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []

    slots: list[dict[str, int]] = []
    for slot in value:
        if not isinstance(slot, dict):
            continue
        opening_hour = _as_int(slot.get("openingHour"))
        opening_minute = _as_int(slot.get("openingMinute"))
        closing_hour = _as_int(slot.get("closingHour"))
        closing_minute = _as_int(slot.get("closingMinute"))
        values = (opening_hour, opening_minute, closing_hour, closing_minute)
        if any(item is None for item in values):
            continue
        if not all(0 <= item <= 59 for item in (opening_minute, closing_minute)):
            continue
        if not all(0 <= item <= 23 for item in (opening_hour, closing_hour)):
            continue
        slots.append(
            {
                "opening_hour": opening_hour,
                "opening_minute": opening_minute,
                "closing_hour": closing_hour,
                "closing_minute": closing_minute,
            }
        )
    return sorted(slots, key=lambda slot: (slot["opening_hour"], slot["opening_minute"]))


def _as_nonempty_string(value: Any) -> str | None:
    """Return a source string only when present."""
    return value if isinstance(value, str) and value else None


def _as_int(value: Any) -> int | None:
    """Convert genuinely numeric source values without coercing labels."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
