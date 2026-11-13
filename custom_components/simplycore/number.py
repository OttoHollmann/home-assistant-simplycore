"""Number controls for SimplyCore."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HEATING_MODES
from .coordinator import SimplyCoreCoordinator
from .entity import SimplyCoreEntity

DEFAULT_PRESET_TEMPERATURES = {1: 17.0, 2: 22.0, 3: 30.0}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the heating preset slider."""
    coordinator: SimplyCoreCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SimplyCoreHeatingPresetSlider(coordinator, entry),
            SimplyCoreDefaultHeatingPresetSlider(coordinator, entry, "normal"),
            SimplyCoreDefaultHeatingPresetSlider(coordinator, entry, "minimal"),
        ]
    )


class SimplyCoreHeatingPresetSlider(SimplyCoreEntity, NumberEntity):
    """Choose one of the unit's reported heating presets with a temperature slider."""

    _attr_translation_key = "heating_preset_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self, coordinator: SimplyCoreCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the preset slider."""
        super().__init__(coordinator, entry, "heating_preset_temperature")

    @property
    def native_min_value(self) -> float:
        """Return the lowest configured preset temperature."""
        return min(self._preset_temperatures().values())

    @property
    def native_max_value(self) -> float:
        """Return the highest configured preset temperature."""
        return max(self._preset_temperatures().values())

    @property
    def native_value(self) -> float | None:
        """Return the temperature of the active preset reported by the unit."""
        mode = (self.coordinator.data or {}).get("activeHeatingMode")
        if mode is None:
            return None
        try:
            return self._preset_temperatures().get(int(mode))
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Select the closest supported preset; this does not set an exact temperature."""
        presets = self._preset_temperatures()
        mode = min(presets, key=lambda preset: abs(presets[preset] - value))
        await self.coordinator.async_send_command(
            "unit.setHeatingMode", {"mode": mode}
        )

    def _preset_temperatures(self) -> dict[int, float]:
        """Read configured preset temperatures, falling back to observed defaults."""
        configuration = (self.coordinator.data or {}).get(
            "heatingModeConfiguration", {}
        )
        if not isinstance(configuration, dict):
            configuration = {}
        return {
            mode: float(
                configuration.get(
                    f"mode{mode}Temperature", DEFAULT_PRESET_TEMPERATURES[mode]
                )
            )
            for mode in map(int, HEATING_MODES)
        }


class SimplyCoreDefaultHeatingPresetSlider(SimplyCoreHeatingPresetSlider):
    """Choose the default heating preset for a ventilation mode."""

    def __init__(
        self,
        coordinator: SimplyCoreCoordinator,
        entry: ConfigEntry,
        ventilation_mode: str,
    ) -> None:
        """Initialize a ventilation-mode default preset slider."""
        super().__init__(coordinator, entry)
        self._ventilation_mode = ventilation_mode
        suffix = "normal" if ventilation_mode == "normal" else "vacation"
        self._attr_unique_id = (
            f"{entry.entry_id}_default_heating_preset_{suffix}"
        )
        self._attr_translation_key = f"default_heating_preset_{suffix}"

    @property
    def native_value(self) -> float | None:
        """Return the configured default preset temperature."""
        configuration = (self.coordinator.data or {}).get(
            "ventilationModeConfiguration", {}
        )
        if not isinstance(configuration, dict):
            return None
        key = f"{self._ventilation_mode}VentilationModeTemperatureMode"
        mode = configuration.get(key)
        if mode is None:
            return None
        try:
            return self._preset_temperatures().get(int(mode))
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the ventilation mode's nearest supported heating preset."""
        presets = self._preset_temperatures()
        mode = min(presets, key=lambda preset: abs(presets[preset] - value))
        await self.coordinator.async_set_ventilation_heating_mode(
            self._ventilation_mode, mode
        )
