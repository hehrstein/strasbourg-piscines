"""Open-state sensors for Strasbourg's public pools."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import StrasbourgPiscinesCoordinator
from .sensor import StrasbourgPoolEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one open/closed sensor for each selected pool."""
    coordinator: StrasbourgPiscinesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            StrasbourgPoolOpenSensor(coordinator, entry, pool_id)
            for pool_id in coordinator.pool_ids
        ]
    )


class StrasbourgPoolOpenSensor(StrasbourgPoolEntity, BinarySensorEntity):
    """Expose the explicit open/closed value published by the source."""

    _attr_icon = "mdi:pool"
    _attr_name = "Ouverte"

    def __init__(
        self,
        coordinator: StrasbourgPiscinesCoordinator,
        entry: ConfigEntry,
        pool_id: str,
    ) -> None:
        """Initialize the pool open-state entity."""
        super().__init__(coordinator, entry, pool_id)
        self._attr_unique_id = f"{entry.entry_id}_{pool_id.casefold()}_open"

    @property
    def is_on(self) -> bool | None:
        """Return only the explicit source value, including unknown when absent."""
        pool = self._pool_data
        return pool.get("is_open") if pool else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the same contextual information as the source sensors."""
        return self._pool_attributes
