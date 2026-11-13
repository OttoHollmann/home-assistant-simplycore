"""SimplyCore Home Assistant integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_ENABLED,
    SERVICE_ENTRY_ID,
    SERVICE_EVENTS,
    SERVICE_SET_SCHEDULE,
)
from .coordinator import SimplyCoreCoordinator, validate_schedule_event

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
]

SCHEDULE_EVENT_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("start"): cv.string,
            vol.Required("end"): cv.string,
            vol.Required("day"): vol.All(int, vol.Range(min=0, max=6)),
        }
    ),
    validate_schedule_event,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SimplyCore from a config entry."""
    coordinator = SimplyCoreCoordinator(hass, entry)
    try:
        await coordinator.async_connect()
    except Exception as err:
        await coordinator.async_close()
        raise ConfigEntryNotReady("Unable to connect to the SimplyCore unit") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _register_schedule_service(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a SimplyCore config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SimplyCoreCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_close()
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_SCHEDULE)
    return unload_ok


def _register_schedule_service(hass: HomeAssistant) -> None:
    """Register a service for configuring custom weekly ventilation events."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    async def async_set_schedule(call: ServiceCall) -> None:
        """Send a custom schedule to the selected unit."""
        coordinator: SimplyCoreCoordinator | None = hass.data.get(DOMAIN, {}).get(
            call.data[SERVICE_ENTRY_ID]
        )
        if coordinator is None:
            raise HomeAssistantError("Unknown SimplyCore config entry")
        await coordinator.async_set_schedule(
            call.data[SERVICE_EVENTS], call.data.get(SERVICE_ENABLED)
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        async_set_schedule,
        schema=vol.Schema(
            {
                vol.Required(SERVICE_ENTRY_ID): cv.string,
                vol.Required(SERVICE_EVENTS): [SCHEDULE_EVENT_SCHEMA],
                vol.Optional(SERVICE_ENABLED): bool,
            }
        ),
    )
