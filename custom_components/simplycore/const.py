"""Constants for the SimplyCore integration."""

DOMAIN = "simplycore"
API_URL = "https://simplycore.fromargo.com"
SOCKET_IO_PATH = "socket.io"
SOCKET_AUTH_TOKEN = "simplyAirCore"
DEFAULT_LOCALE = "en"

CONF_AUTH_TOKEN = "auth_token"
CONF_NAME = "name"

EVENT_UNIT_STATE = "unit_state"

VENTILATION_MODES = ["normal", "minimal"]
HEATING_MODES = ["1", "2", "3"]
WEEKDAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_ENTRY_ID = "entry_id"
SERVICE_EVENTS = "events"
SERVICE_ENABLED = "enabled"
