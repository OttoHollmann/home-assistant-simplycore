"""Binary sensors for SimplyCore."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SimplyCoreCoordinator, boost_remaining_seconds
from .entity import SimplyCoreEntity


@dataclass(frozen=True, kw_only=True)
class SimplyCoreBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a SimplyCore binary sensor."""


BINARY_SENSORS: tuple[SimplyCoreBinarySensorDescription, ...] = (
    SimplyCoreBinarySensorDescription(
        key="powered",
        translation_key="powered",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    SimplyCoreBinarySensorDescription(
        key="boost1Active",
        translation_key="bathroom_boost_active",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    SimplyCoreBinarySensorDescription(
        key="boost2Active",
        translation_key="kitchen_boost_active",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    SimplyCoreBinarySensorDescription(
        key="boostFullActive",
        translation_key="full_apartment_boost_active",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    SimplyCoreBinarySensorDescription(
        key="incomingAirHeating",
        translation_key="ventilation_air_heating_active",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    SimplyCoreBinarySensorDescription(
        key="centralHeatingDemand",
        translation_key="central_heating_demand_estimated",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SimplyCore binary sensors."""
    coordinator: SimplyCoreCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SimplyCoreBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class SimplyCoreBinarySensor(SimplyCoreEntity, BinarySensorEntity):
    """Represent a SimplyCore binary sensor."""

    entity_description: SimplyCoreBinarySensorDescription

    def __init__(
        self,
        coordinator: SimplyCoreCoordinator,
        entry: ConfigEntry,
        description: SimplyCoreBinarySensorDescription,
    ) -> None:
        """Initialize a binary sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return whether the represented state is active."""
        state = self.coordinator.data or {}
        boost_sensor = {
            "boost1Active": ("boosted1", "boost1"),
            "boost2Active": ("boosted2", "boost2"),
            "boostFullActive": ("boostedFull", "boostFull"),
        }.get(self.entity_description.key)
        if boost_sensor is not None:
            state_key, boost = boost_sensor
            active = state.get(state_key)
            if active is None:
                return None
            if not _is_true(active):
                return False
            remaining = boost_remaining_seconds(
                state, boost, self.coordinator.boost_started_at(boost)
            )
            return remaining is None or remaining > 0
        if self.entity_description.key == "centralHeatingDemand":
            requested = state.get("requestedTemperature")
            room_temperature = state.get("temperatureSlot1")
            if not isinstance(requested, (int, float)) or not isinstance(
                room_temperature, (int, float)
            ):
                return None
            return requested > room_temperature
        value = state.get("powered")
        if self.entity_description.key == "incomingAirHeating":
            value = state.get("incomingAirHeating")
        return _is_true(value) if value is not None else None


def _is_true(value: Any) -> bool:
    """Normalize booleans and numeric/string boolean values."""
    return value is True or value == 1 or (
        isinstance(value, str) and value.lower() in {"true", "on", "yes", "1"}
    )
