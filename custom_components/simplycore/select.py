"""Select controls for SimplyCore."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HEATING_MODES, VENTILATION_MODES
from .coordinator import SimplyCoreCoordinator
from .entity import SimplyCoreEntity


@dataclass(frozen=True, kw_only=True)
class SimplyCoreSelectDescription(SelectEntityDescription):
    """Describe a SimplyCore select."""

    command: str


SELECTS: tuple[SimplyCoreSelectDescription, ...] = (
    SimplyCoreSelectDescription(
        key="ventilationMode",
        translation_key="ventilation_mode",
        options=VENTILATION_MODES,
        command="unit.setVentilationMode",
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SimplyCore selects."""
    coordinator: SimplyCoreCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SimplyCoreSelect(coordinator, entry, description) for description in SELECTS
    )


class SimplyCoreSelect(SimplyCoreEntity, SelectEntity):
    """Represent a SimplyCore select control."""

    entity_description: SimplyCoreSelectDescription

    def __init__(
        self,
        coordinator: SimplyCoreCoordinator,
        entry: ConfigEntry,
        description: SimplyCoreSelectDescription,
    ) -> None:
        """Initialize a select."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description
        self._attr_options = list(description.options or [])

    @property
    def options(self) -> list[str]:
        """Return translated ventilation mode labels when provided by the unit."""
        if self.entity_description.key != "ventilationMode":
            return self._attr_options
        theme = (self.coordinator.data or {}).get("localizedTheme", {})
        if not isinstance(theme, dict):
            theme = {}
        language = self.coordinator.hass.config.language or "en"
        localized = theme.get(language) or theme.get(language.split("-")[0])
        if not isinstance(localized, dict):
            localized = theme.get("en", {})
        if not isinstance(localized, dict):
            localized = {}
        return [
            localized.get("NormalVentilationModeLabel") or "normal",
            localized.get("MinimalVentilationModeLabel") or "Vacation",
        ]

    @property
    def current_option(self) -> str | None:
        """Return the selected option reported by the unit."""
        value = (self.coordinator.data or {}).get(self.entity_description.key)
        if self.entity_description.key == "ventilationMode":
            index = {"normal": 0, "minimal": 1}.get(value)
            return self.options[index] if index is not None else None
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Send a mode selection to the unit."""
        if option not in self.options:
            raise ValueError(f"Unsupported SimplyCore option: {option}")
        if self.entity_description.key == "ventilationMode":
            value: str | int = VENTILATION_MODES[self.options.index(option)]
        else:
            value = (
                int(option)
                if self.entity_description.key == "activeHeatingMode"
                else option
            )
        await self.coordinator.async_send_command(
            self.entity_description.command, {"mode": value}
        )
