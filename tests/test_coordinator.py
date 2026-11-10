"""Tests for the shared Strasbourg Piscines coordinator."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.util import dt as dt_util

from custom_components.strasbourg_piscines import coordinator as coordinator_module
from custom_components.strasbourg_piscines.api import StrasbourgPiscinesResult
from custom_components.strasbourg_piscines.const import (
    CONF_POOLS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


class FakePoolApiClient:
    """Pool API client returning a deterministic source response."""

    async def async_get_pools(self) -> StrasbourgPiscinesResult:
        return StrasbourgPiscinesResult(
            {
                "first": {"id": "first", "name": "First"},
                "second": {"id": "second", "name": "Second"},
            },
            dt_util.utcnow(),
        )


def make_entry(pool_ids: list[str], interval: int = 3) -> MockConfigEntry:
    """Create a deterministic config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        entry_id="test-entry",
        data={CONF_POOLS: pool_ids, CONF_SCAN_INTERVAL: interval},
    )


async def test_coordinator_keeps_only_selected_pools(
    hass, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One source request feeds only the selected Home Assistant devices."""
    monkeypatch.setattr(
        coordinator_module,
        "StrasbourgPiscinesApiClient",
        lambda _hass: FakePoolApiClient(),
    )
    coordinator = coordinator_module.StrasbourgPiscinesCoordinator(
        hass, make_entry(["second", "missing"])
    )

    data = await coordinator._async_update_data()

    assert data["pools"] == {"second": {"id": "second", "name": "Second"}}
    assert data["fetched_at"]


def test_update_interval_enforces_source_refresh_floor() -> None:
    """A legacy setting cannot poll the public feed faster than three minutes."""
    assert coordinator_module._update_interval(1) == timedelta(minutes=3)
