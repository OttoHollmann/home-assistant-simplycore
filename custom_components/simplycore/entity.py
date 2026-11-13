"""Base entity for SimplyCore."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SimplyCoreCoordinator


class SimplyCoreEntity(CoordinatorEntity[SimplyCoreCoordinator]):
    """Common SimplyCore entity metadata and availability."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SimplyCoreCoordinator, entry: ConfigEntry, unique_id: str
    ) -> None:
        """Initialize a SimplyCore entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{unique_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="SimplyCore",
            model="Ventilation unit",
        )

    @property
    def available(self) -> bool:
        """Return whether a live connection and state are available."""
        return self.coordinator.connected and self.coordinator.data is not None
