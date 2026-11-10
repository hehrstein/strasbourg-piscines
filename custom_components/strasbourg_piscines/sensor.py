"""Sensors for Strasbourg's public pools."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_ATTRIBUTION, DATA_SOURCE_URL, DOMAIN
from .coordinator import StrasbourgPiscinesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up source-status and today's-hours sensors for selected pools."""
    coordinator: StrasbourgPiscinesCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for pool_id in coordinator.pool_ids:
        entities.extend(
            [
                StrasbourgPoolOccupancySensor(coordinator, entry, pool_id),
                StrasbourgPoolScheduleSensor(coordinator, entry, pool_id),
            ]
        )
    async_add_entities(entities)


class StrasbourgPoolEntity(CoordinatorEntity[StrasbourgPiscinesCoordinator]):
    """Shared implementation for entities representing one pool."""

    _attr_attribution = DATA_ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: StrasbourgPiscinesCoordinator,
        entry: ConfigEntry,
        pool_id: str,
    ) -> None:
        """Initialize an entity with its stable source identifier."""
        super().__init__(coordinator)
        self._pool_id = pool_id
        pool = self._pool_data or {}
        pool_name = pool.get("name") or pool_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, pool_id)},
            name=f"Strasbourg — {pool_name}",
            manufacturer="Eurométropole de Strasbourg",
            model="Piscine publique",
            configuration_url=DATA_SOURCE_URL,
        )

    @property
    def _pool_data(self) -> dict[str, Any] | None:
        """Return the current source record for this pool."""
        pool = self.coordinator.data.get("pools", {}).get(self._pool_id)
        return pool if isinstance(pool, dict) else None

    @property
    def _pool_attributes(self) -> dict[str, Any]:
        """Expose source data and freshness without inventing measurements."""
        pool = self._pool_data
        if pool is None:
            return {
                "pool_id": self._pool_id,
                "data_source": DATA_ATTRIBUTION,
                "data_fetched_at": self.coordinator.data.get("fetched_at"),
            }
        return {
            "pool_id": self._pool_id,
            "pool_name": pool.get("name"),
            "is_open": pool.get("is_open"),
            "realtime_status": pool.get("realtime_status"),
            "occupation": pool.get("occupation"),
            "today_schedule": pool.get("today_schedule"),
            "source_updated_at": pool.get("source_updated_at"),
            "types": pool.get("types"),
            "data_source": DATA_ATTRIBUTION,
            "data_fetched_at": self.coordinator.data.get("fetched_at"),
        }


class StrasbourgPoolOccupancySensor(StrasbourgPoolEntity, SensorEntity):
    """Expose the exact real-time occupancy status code published by the city."""

    _attr_icon = "mdi:account-group"
    _attr_name = "Affluence"

    def __init__(
        self,
        coordinator: StrasbourgPiscinesCoordinator,
        entry: ConfigEntry,
        pool_id: str,
    ) -> None:
        """Initialize the occupancy-status sensor."""
        super().__init__(coordinator, entry, pool_id)
        self._attr_unique_id = f"{entry.entry_id}_{pool_id.casefold()}_occupancy"

    @property
    def native_value(self) -> str | None:
        """Return the source code (GREEN, ORANGE, RED, BLACK or CLOSED)."""
        pool = self._pool_data
        return pool.get("realtime_status") if pool else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return contextual source data and freshness details."""
        return self._pool_attributes


class StrasbourgPoolScheduleSensor(StrasbourgPoolEntity, SensorEntity):
    """Expose the public opening slots published for the current day."""

    _attr_icon = "mdi:clock-outline"
    _attr_name = "Horaires du jour"

    def __init__(
        self,
        coordinator: StrasbourgPiscinesCoordinator,
        entry: ConfigEntry,
        pool_id: str,
    ) -> None:
        """Initialize the schedule sensor."""
        super().__init__(coordinator, entry, pool_id)
        self._attr_unique_id = f"{entry.entry_id}_{pool_id.casefold()}_today_schedule"

    @property
    def native_value(self) -> str | None:
        """Format the source's slots only; an absent schedule stays unknown."""
        pool = self._pool_data
        schedule = pool.get("today_schedule") if pool else None
        if not schedule:
            return None
        return " · ".join(
            f"{slot['opening_hour']:02}:{slot['opening_minute']:02}–"
            f"{slot['closing_hour']:02}:{slot['closing_minute']:02}"
            for slot in schedule
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return source status and individual schedule slots."""
        return self._pool_attributes
