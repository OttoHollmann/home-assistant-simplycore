"""Socket.IO client and state coordinator for SimplyCore."""

from __future__ import annotations

import logging
import math
import re
from copy import deepcopy
from datetime import datetime, time
from typing import Any

import socketio
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    API_URL,
    CONF_AUTH_TOKEN,
    DEFAULT_LOCALE,
    DOMAIN,
    EVENT_UNIT_STATE,
    SOCKET_AUTH_TOKEN,
    SOCKET_IO_PATH,
)


class SimplyCoreCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage a SimplyCore Socket.IO connection and live unit state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator and Socket.IO client."""
        super().__init__(hass, logger=logging.getLogger(__name__), name=DOMAIN)
        self._auth_token: str = entry.data[CONF_AUTH_TOKEN]
        self._client = socketio.AsyncClient(
            reconnection=True,
            logger=False,
            engineio_logger=False,
        )
        self.connected = False
        self._boost_started_at: dict[str, datetime] = {}

        self._client.on("connect", self._async_connected)
        self._client.on("disconnect", self._async_disconnected)
        self._client.on(EVENT_UNIT_STATE, self._async_unit_state)

    async def async_connect(self) -> None:
        """Connect to the cloud service."""
        await self._client.connect(
            API_URL,
            socketio_path=SOCKET_IO_PATH,
            transports=["websocket"],
            auth={"token": SOCKET_AUTH_TOKEN},
        )

    async def async_close(self) -> None:
        """Close the cloud connection."""
        if self._client.connected:
            await self._client.disconnect()

    async def _async_connected(self) -> None:
        """Subscribe to the unit after initial connection and every reconnect."""
        self.connected = True
        try:
            await self._client.emit(
                "unit.subscribe",
                {
                    "authToken": self._auth_token,
                    "locale": (self.hass.config.language or DEFAULT_LOCALE)
                    .split("-")[0]
                    .lower(),
                },
            )
        except Exception:
            self.connected = False
            raise
        self.async_set_updated_data(dict(self.data or {}))

    async def _async_disconnected(self, reason: str | None = None) -> None:
        """Mark the unit unavailable after a disconnect."""
        self.connected = False
        self.async_set_updated_data(dict(self.data or {}))

    async def _async_unit_state(self, payload: Any) -> None:
        """Store unit state received from the service."""
        if not isinstance(payload, dict):
            return
        state = payload.get("data", payload)
        if not isinstance(state, dict):
            return
        now = dt_util.utcnow()
        for boost, state_key in (
            ("boost1", "boosted1"),
            ("boost2", "boosted2"),
            ("boostFull", "boostedFull"),
        ):
            active = state.get(state_key)
            if active is None:
                continue
            if _is_true(active):
                self._boost_started_at.setdefault(boost, now)
            else:
                self._boost_started_at.pop(boost, None)
        self.async_set_updated_data(_without_credentials(state))

    def boost_started_at(self, boost: str) -> datetime | None:
        """Return the local start time for an active boost without API timing data."""
        return self._boost_started_at.get(boost)

    async def async_send_command(self, event: str, payload: dict[str, Any]) -> None:
        """Send a documented command to the unit."""
        if not self.connected or not self._client.connected:
            raise HomeAssistantError("SimplyCore is not connected")
        try:
            await self._client.emit(
                event,
                {"authToken": self._auth_token, **payload},
            )
        except Exception as err:
            raise HomeAssistantError(
                f"Unable to send SimplyCore command {event}"
            ) from err

    async def async_set_schedule_enabled(self, enabled: bool) -> None:
        """Change schedule enablement while preserving all other schedule fields."""
        schedule = deepcopy((self.data or {}).get("schedule", {}))
        if not isinstance(schedule, dict):
            schedule = {}
        schedule["enabled"] = enabled
        await self.async_send_command("unit.setSchedule", {"schedule": schedule})

    async def async_set_schedule(
        self, events: list[dict[str, Any]], enabled: bool | None = None
    ) -> None:
        """Set custom minimal-ventilation events while preserving other schedule data."""
        schedule = deepcopy((self.data or {}).get("schedule", {}))
        if not isinstance(schedule, dict):
            schedule = {}
        schedule["minimalVentilationEvents"] = events
        if enabled is not None:
            schedule["enabled"] = enabled
        await self.async_send_command("unit.setSchedule", {"schedule": schedule})

    async def async_set_ventilation_heating_mode(
        self, ventilation_mode: str, heating_mode: int
    ) -> None:
        """Set the heating preset associated with a ventilation mode."""
        configuration = deepcopy(
            (self.data or {}).get("ventilationModeConfiguration", {})
        )
        if not isinstance(configuration, dict):
            configuration = {}
        key = f"{ventilation_mode}VentilationModeTemperatureMode"
        configuration[key] = heating_mode
        await self.async_send_command(
            "unit.setVentilationModeConfiguration",
            {"configuration": configuration},
        )


def _without_credentials(value: Any) -> Any:
    """Remove credential-like keys from data that may be exposed as entity attributes."""
    if isinstance(value, dict):
        return {
            key: _without_credentials(item)
            for key, item in value.items()
            if key.lower() not in {"token", "authtoken"}
        }
    if isinstance(value, list):
        return [_without_credentials(item) for item in value]
    return value


def boost_remaining_seconds(
    state: dict[str, Any], boost: str, started_at: datetime | None = None
) -> int | None:
    """Return seconds remaining for a boost, or None when its state is unknown."""
    timing = {
        "boost1": ("boosted1", "boost1End", "boost1Start", "boost1Duration"),
        "boost2": ("boosted2", "boost2End", "boost2Start", "boost2Duration"),
        "boostFull": (
            "boostedFull",
            "fullBoostEnd",
            "fullBoostStart",
            "boostFullDuration",
        ),
    }
    state_key, end_key, start_key, duration_key = timing[boost]
    active = state.get(state_key)
    if active is None:
        return None
    if not (
        active is True
        or active == 1
        or (isinstance(active, str) and active.lower() in {"true", "on", "yes", "1"})
    ):
        return 0

    end_time = _parse_datetime(state.get(end_key))
    if end_time is None:
        start_time = _parse_datetime(state.get(start_key))
        if start_time is None:
            start_time = started_at
        duration = state.get(duration_key)
        if start_time is None or not isinstance(duration, (int, float)):
            return None
        from datetime import timedelta

        end_time = start_time + timedelta(seconds=duration)

    remaining = (dt_util.as_utc(end_time) - dt_util.utcnow()).total_seconds()
    return max(0, math.ceil(remaining))


def _parse_datetime(value: Any):
    """Parse an API timestamp, ignoring missing or malformed values."""
    if not isinstance(value, str):
        return None
    try:
        return dt_util.parse_datetime(value)
    except (TypeError, ValueError):
        return None


def _is_true(value: Any) -> bool:
    """Normalize booleans and numeric/string boolean values."""
    return value is True or value == 1 or (
        isinstance(value, str) and value.lower() in {"true", "on", "yes", "1"}
    )


def validate_schedule_event(event: dict[str, Any]) -> dict[str, Any]:
    """Validate a schedule event without assuming the service's day numbering."""
    if not 0 <= event["day"] <= 6:
        raise vol.Invalid("Schedule day must be an integer from 0 to 6")
    for field in ("start", "end"):
        value = event[field]
        if not isinstance(value, str) or not re.fullmatch(
            r"\d{2}:\d{2}(?::\d{2})?", value
        ):
            raise vol.Invalid(f"Schedule {field} must use HH:MM format")
        try:
            parsed_time = time.fromisoformat(value)
        except ValueError as err:
            raise vol.Invalid(f"Schedule {field} must be a valid time") from err
        event[field] = parsed_time.strftime("%H:%M")
    return event
