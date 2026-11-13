"""Buttons for SimplyCore."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SimplyCoreCoordinator
from .entity import SimplyCoreEntity

BOOST_LABELS = {
    "en": ("Boost", "Bathroom", "Kitchen", "Full Apartment"),
    "cs": ("Nárazové větrání", "Koupelna", "Kuchyně", "Celý byt"),
    "da": ("Boost", "Badeværelse", "Køkken", "Hele lejligheden"),
    "de": ("Boost", "Badezimmer", "Küche", "Ganze Wohnung"),
    "fi": ("Tehostus", "Kylpyhuone", "Keittiö", "Koko asunto"),
    "hu": ("Intenzív szellőztetés", "Fürdőszoba", "Konyha", "Teljes lakás"),
    "it": ("Boost", "Bagno", "Cucina", "Intero appartamento"),
    "pl": ("Boost", "Łazienka", "Kuchnia", "Całe mieszkanie"),
    "es": ("Ventilación intensiva", "Baño", "Cocina", "Apartamento completo"),
    "sv": ("Boost", "Badrum", "Kök", "Hela lägenheten"),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SimplyCore buttons."""
    coordinator: SimplyCoreCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SimplyCoreBoostButton(coordinator, entry, 1),
            SimplyCoreBoostButton(coordinator, entry, 2),
            SimplyCoreBoostButton(coordinator, entry, 3),
        ]
    )


class SimplyCoreBoostButton(SimplyCoreEntity, ButtonEntity):
    """Start a bathroom, kitchen, or whole-apartment boost."""

    def __init__(
        self, coordinator: SimplyCoreCoordinator, entry: ConfigEntry, boost: int
    ) -> None:
        """Initialize the boost button."""
        super().__init__(coordinator, entry, f"boost_{boost}")
        self._boost = boost

    @property
    def name(self) -> str:
        """Return the unit-localized name for this boost."""
        theme = (self.coordinator.data or {}).get("localizedTheme", {})
        if not isinstance(theme, dict):
            theme = {}
        language = self.coordinator.hass.config.language or "en"
        language = language.split("-")[0].lower()
        language_theme = theme.get(language)
        if not isinstance(language_theme, dict):
            language_theme = theme.get("en", {})
        if not isinstance(language_theme, dict):
            language_theme = {}
        prefix, bathroom, kitchen, full_apartment = BOOST_LABELS.get(
            language, BOOST_LABELS["en"]
        )
        if self._boost == 1:
            label = language_theme.get("Boost1Label") or bathroom
        elif self._boost == 2:
            label = language_theme.get("Boost2Label") or kitchen
        else:
            label = full_apartment
        return f"{prefix} {label}"

    async def async_press(self) -> None:
        """Start this boost mode."""
        await self.coordinator.async_send_command(
            "unit.startBoost",
            {"boost": "full" if self._boost == 3 else self._boost},
        )
