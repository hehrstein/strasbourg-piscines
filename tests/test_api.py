"""Tests for Strasbourg's public real-time pool feed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.strasbourg_piscines.api import StrasbourgPiscinesApiClient

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


class FakeResponse:
    """Minimal aiohttp response fixture."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit the mocked response."""

    def raise_for_status(self) -> None:
        """Simulate a successful Open Data response."""

    async def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    """Minimal HTTP session fixture."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls = 0

    def get(self, *args: Any, **kwargs: Any) -> FakeResponse:
        self.calls += 1
        return FakeResponse(self._payload)


async def test_client_normalizes_real_time_pool_response(
    hass, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Source fields become stable Home Assistant values without guesswork."""
    fixture_path = Path(__file__).parent / "fixtures" / "pools.json"
    session = FakeSession(json.loads(fixture_path.read_text("utf-8")))
    monkeypatch.setattr(
        "custom_components.strasbourg_piscines.api.async_get_clientsession",
        lambda _hass: session,
    )

    result = await StrasbourgPiscinesApiClient(hass).async_get_pools()

    assert session.calls == 1
    assert set(result.pools) == {"401_SPO_2", "402_SPO_3"}
    assert result.pools["401_SPO_2"] == {
        "id": "401_SPO_2",
        "name": "Centre nautique de Schiltigheim",
        "is_open": True,
        "realtime_status": "GREEN",
        "occupation": 62,
        "today_schedule": [
            {
                "opening_hour": 6,
                "opening_minute": 30,
                "closing_hour": 19,
                "closing_minute": 0,
            }
        ],
        "source_updated_at": "2026-11-10 10:12:22",
        "types": "Cat_06_05",
    }


def test_parser_preserves_unknown_open_state() -> None:
    """Undocumented open-state values must not be guessed."""
    from custom_components.strasbourg_piscines.api import _normalize_pool

    pool = _normalize_pool({"name": "Test", "sigid": "test", "isopen": 9})

    assert pool is not None
    assert pool["is_open"] is None
