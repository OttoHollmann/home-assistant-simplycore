"""Sensors for SimplyCore."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SimplyCoreCoordinator, boost_remaining_seconds
from .entity import SimplyCoreEntity


@dataclass(frozen=True, kw_only=True)
class SimplyCoreSensorDescription(SensorEntityDescription):
    """Describe a SimplyCore sensor."""


SENSORS: tuple[SimplyCoreSensorDescription, ...] = (
    SimplyCoreSensorDescription(
        key="currentFlowSupply",
        translation_key="supply_airflow",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="currentFlowExhaust",
        translation_key="exhaust_airflow",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="temperatureSupply",
        translation_key="supply_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="temperatureOutside",
        translation_key="outside_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="temperatureSlot1",
        translation_key="temperature_sensor_1",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="co2Slot1",
        translation_key="co2_sensor_1",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement="ppm",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="requestedTemperature",
        translation_key="requested_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="boost1Remaining",
        translation_key="bathroom_boost_time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="boost2Remaining",
        translation_key="kitchen_boost_time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="boostFullRemaining",
        translation_key="full_apartment_boost_time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SimplyCoreSensorDescription(
        key="unitCondition", translation_key="unit_condition"
    ),
    SimplyCoreSensorDescription(
        key="ventilationMode", translation_key="ventilation_mode"
    ),
    SimplyCoreSensorDescription(
        key="activeHeatingMode", translation_key="active_heating_mode"
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SimplyCore sensors."""
    coordinator: SimplyCoreCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SimplyCoreSensor(coordinator, entry, description) for description in SENSORS
    )


class SimplyCoreSensor(SimplyCoreEntity, SensorEntity):
    """Represent a SimplyCore sensor."""

    entity_description: SimplyCoreSensorDescription

    def __init__(
        self,
        coordinator: SimplyCoreCoordinator,
        entry: ConfigEntry,
        description: SimplyCoreSensorDescription,
    ) -> None:
        """Initialize a sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Refresh countdown values every second while the entity is loaded."""
        await super().async_added_to_hass()
        if self.entity_description.key.endswith("Remaining"):
            self.async_on_remove(
                async_track_time_interval(
                    self.hass,
                    self._async_update_countdown,
                    timedelta(seconds=1),
                )
            )

    @callback
    def _async_update_countdown(self, now: datetime) -> None:
        """Update the displayed countdown between cloud state messages."""
        if self.native_value is not None:
            self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        boost = {
            "boost1Remaining": "boost1",
            "boost2Remaining": "boost2",
            "boostFullRemaining": "boostFull",
        }.get(self.entity_description.key)
        if boost is not None:
            return boost_remaining_seconds(
                self.coordinator.data or {},
                boost,
                self.coordinator.boost_started_at(boost),
            )
        return (self.coordinator.data or {}).get(self.entity_description.key)
