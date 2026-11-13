"""Config flow for SimplyCore."""

from __future__ import annotations

import asyncio
import hashlib
from urllib.parse import SplitResult, parse_qs, unquote, urljoin, urlsplit

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_AUTH_TOKEN, CONF_NAME, DOMAIN


class SimplyCoreConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SimplyCore."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Set up a SimplyCore unit."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                token = await _async_extract_token(
                    self.hass, user_input[CONF_AUTH_TOKEN]
                )
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors[CONF_AUTH_TOKEN] = "cannot_resolve_link"
                token = ""
            if not token:
                errors.setdefault(CONF_AUTH_TOKEN, "invalid_token")
            else:
                await self.async_set_unique_id(
                    hashlib.sha256(token.encode()).hexdigest()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME].strip() or "SimplyCore",
                    data={CONF_AUTH_TOKEN: token},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_TOKEN): str,
                    vol.Optional(CONF_NAME, default="SimplyCore"): str,
                }
            ),
            errors=errors,
        )


async def _async_extract_token(hass, value: str) -> str:
    """Extract a token from raw input or resolve a QR air-link."""
    value = value.strip()
    if not value.startswith(("https://", "http://")):
        return value

    token = _extract_simplycore_link_token(value)
    if token:
        return token

    if _parse_trusted_url(value, "air-link.simplycontrol.cz") is None:
        return ""

    token = _extract_air_link_token(value)
    if token:
        return token

    session = async_get_clientsession(hass)
    current_url = value
    for _ in range(5):
        parsed = _parse_trusted_url(current_url, "air-link.simplycontrol.cz")
        if parsed is None:
            token = _extract_simplycore_link_token(current_url)
            return token
        token = _extract_air_link_token(current_url)
        if token:
            return token
        if parsed.path in {"", "/"}:
            return ""

        async with session.get(current_url, allow_redirects=False) as response:
            if response.status not in {301, 302, 303, 307, 308}:
                return ""
            location = response.headers.get("Location")
        if not location:
            return ""

        current_url = urljoin(current_url, location.strip())
        token = _extract_simplycore_link_token(current_url)
        if token:
            return token

    return ""


def _extract_simplycore_link_token(value: str) -> str:
    """Extract the token from a SimplyCore share link."""
    parsed = _parse_trusted_url(value, "simplycore-link.simplycontrol.cz")
    if parsed is None:
        return ""
    if parsed.path.startswith("/code="):
        return unquote(parsed.path.removeprefix("/code=")).strip()
    return parse_qs(parsed.query).get("code", [""])[0].strip()


def _extract_air_link_token(value: str) -> str:
    """Extract the token from the air-link redirect query."""
    parsed = _parse_trusted_url(value, "air-link.simplycontrol.cz")
    if parsed is None:
        return ""
    return parse_qs(parsed.query).get("code", [""])[0].strip()


def _parse_trusted_url(value: str, hostname: str) -> SplitResult | None:
    """Parse an HTTPS URL only when it has the expected host and no credentials."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or parsed.hostname != hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        return None
    return parsed
