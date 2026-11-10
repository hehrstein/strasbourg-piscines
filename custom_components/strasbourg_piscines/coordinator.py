"""Shared coordinator for Strasbourg Piscines."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import StrasbourgPiscinesApiClient, StrasbourgPiscinesApiError
from .const import (
    CONF_POOLS,
    CONF_SCAN_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class StrasbourgPiscinesCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch selected municipal pools through one shared Open Data request."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator from the config entry."""
        configured_interval = _configured_value(
            entry, CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL.total_seconds() / 60
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_update_interval(configured_interval),
            config_entry=entry,
        )
        self._client = StrasbourgPiscinesApiClient(hass)
        self._pool_ids = _as_string_list(_configured_value(entry, CONF_POOLS, []))

    @property
    def pool_ids(self) -> list[str]:
        """Return selected stable pool identifiers."""
        return self._pool_ids

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch once and retain only selected pool records."""
        try:
            result = await self._client.async_get_pools()
        except StrasbourgPiscinesApiError as err:
            raise UpdateFailed(str(err)) from err

        return {
            "pools": {
                pool_id: result.pools[pool_id]
                for pool_id in self._pool_ids
                if pool_id in result.pools
            },
            "fetched_at": result.fetched_at.isoformat(),
        }


def _configured_value(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Use options first and retain compatibility with first-entry data."""
    return entry.options.get(key, entry.data.get(key, default))


def _update_interval(value: Any) -> timedelta:
    """Avoid polling the source more often than the integration's floor."""
    try:
        return timedelta(minutes=max(MIN_SCAN_INTERVAL_MINUTES, int(value)))
    except (TypeError, ValueError):
        return DEFAULT_UPDATE_INTERVAL


def _as_string_list(value: Any) -> list[str]:
    """Normalize a config-flow multi-select value."""
    if not isinstance(value, list):
        value = [value] if value else []
    return list(dict.fromkeys(str(item) for item in value if item))
