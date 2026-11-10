"""Tests for Strasbourg Piscines configuration flows."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.data_entry_flow import FlowResultType

from custom_components.strasbourg_piscines import config_flow
from custom_components.strasbourg_piscines.api import StrasbourgPiscinesApiError
from custom_components.strasbourg_piscines.const import (
    CONF_POOLS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_options_flow_renders_when_source_is_unavailable(
    hass, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An outage must render cannot_connect instead of raising AttributeError."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_POOLS: ["401_SPO_2"], CONF_SCAN_INTERVAL: 3},
    )
    entry.add_to_hass(hass)

    async def raise_api_error(_hass: Any) -> list[dict[str, str]]:
        raise StrasbourgPiscinesApiError("Open Data unavailable")

    monkeypatch.setattr(config_flow, "_async_load_choices", raise_api_error)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_select_step_requires_at_least_one_pool(hass) -> None:
    """The integration must not create an empty selection."""
    async def fake_load_choices(_hass: Any) -> list[dict[str, str]]:
        return [{"value": "401_SPO_2", "label": "Schiltigheim"}]

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(config_flow, "_async_load_choices", fake_load_choices)
    try:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_flow.config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_POOLS: [], CONF_SCAN_INTERVAL: 3}
        )
    finally:
        monkeypatch.undo()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "select_pool"}
