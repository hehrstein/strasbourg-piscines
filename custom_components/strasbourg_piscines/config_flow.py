"""Configuration flow for Strasbourg Piscines."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import StrasbourgPiscinesApiClient, StrasbourgPiscinesApiError
from .const import (
    CONF_POOLS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
    NAME,
)


class StrasbourgPiscinesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Strasbourg Piscines setup."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize choices used by the selection step."""
        self._pool_options: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Load the live pool list before creating the entry."""
        errors: dict[str, str] = {}
        try:
            self._pool_options = await _async_load_choices(self.hass)
        except StrasbourgPiscinesApiError:
            errors["base"] = "cannot_connect"
        else:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return await self.async_step_select()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({}), errors=errors
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user choose municipal pools to monitor."""
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = _as_string_list(user_input.get(CONF_POOLS))
            if not selected:
                errors["base"] = "select_pool"
            else:
                return self.async_create_entry(
                    title=NAME,
                    data={
                        CONF_POOLS: selected,
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )

        return self.async_show_form(
            step_id="select",
            data_schema=_selection_schema(self._pool_options),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> StrasbourgPiscinesOptionsFlow:
        """Return the options flow for an existing entry."""
        return StrasbourgPiscinesOptionsFlow()


class StrasbourgPiscinesOptionsFlow(config_entries.OptionsFlow):
    """Handle pool selection and refresh interval changes."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show settings and render safely when the source is unavailable."""
        errors: dict[str, str] = {}
        if not hasattr(self, "_pool_options"):
            # Keep these defaults before the request: an outage must still render
            # the form with cannot_connect, rather than triggering AttributeError.
            self._pool_options: list[dict[str, str]] = []
            try:
                self._pool_options = await _async_load_choices(self.hass)
            except StrasbourgPiscinesApiError:
                errors["base"] = "cannot_connect"

        if user_input is not None and not errors:
            selected = _as_string_list(user_input.get(CONF_POOLS))
            if selected:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_POOLS: selected,
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )
            errors["base"] = "select_pool"

        current_pools = _as_string_list(
            self.config_entry.options.get(
                CONF_POOLS, self.config_entry.data.get(CONF_POOLS, [])
            )
        )
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
            ),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_selection_schema(
                self._pool_options, current_pools, current_interval
            ),
            errors=errors,
        )


async def _async_load_choices(hass: HomeAssistant) -> list[dict[str, str]]:
    """Retrieve source labels for the config and options flows."""
    result = await StrasbourgPiscinesApiClient(hass).async_get_pools()
    return [
        {"value": pool_id, "label": pool["name"]}
        for pool_id, pool in sorted(
            result.pools.items(), key=lambda item: str(item[1]["name"]).casefold()
        )
    ]


def _selection_schema(
    pool_options: list[dict[str, str]],
    selected_pools: list[str] | None = None,
    scan_interval: int | None = None,
) -> vol.Schema:
    """Create the identical setup/options selector schema."""
    return vol.Schema(
        {
            vol.Required(CONF_POOLS, default=selected_pools or []): selector.SelectSelector(
                selector.SelectSelectorConfig(options=pool_options, multiple=True)
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=(
                    scan_interval
                    if scan_interval is not None
                    else DEFAULT_SCAN_INTERVAL_MINUTES
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=MIN_SCAN_INTERVAL_MINUTES,
                    max=MAX_SCAN_INTERVAL_MINUTES,
                ),
            ),
        }
    )


def _as_string_list(value: Any) -> list[str]:
    """Normalize a Home Assistant multi-select value."""
    if not isinstance(value, list):
        value = [value] if value else []
    return list(dict.fromkeys(str(item) for item in value if item))
