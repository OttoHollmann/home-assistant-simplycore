"""Switch controls for SimplyCore."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SimplyCoreCoordinator
from .entity import SimplyCoreEntity


class SimplyCoreScheduleSwitch(SimplyCoreEntity, SwitchEntity):
    """Enable or disable the unit's schedule."""

    _attr_translation_key = "schedule"

    def __init__(
        self, coordinator: SimplyCoreCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the schedule switch."""
        super().__init__(coordinator, entry, "schedule")

    @property
    def is_on(self) -> bool | None:
        """Return schedule enablement."""
        schedule = (self.coordinator.data or {}).get("schedule")
        if not isinstance(schedule, dict) or "enabled" not in schedule:
            return None
        return schedule["enabled"] is True

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the schedule."""
        await self.coordinator.async_set_schedule_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the schedule."""
        await self.coordinator.async_set_schedule_enabled(False)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SimplyCore switches."""
    coordinator: SimplyCoreCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SimplyCoreScheduleSwitch(coordinator, entry)])
