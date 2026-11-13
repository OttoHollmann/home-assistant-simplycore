# SimplyCore Home Assistant integration

This custom integration connects a SimplyCore ventilation unit to Home Assistant
using the facility-issued token encoded in its QR code.

## Disclaimer and support

This is an unofficial community integration. It is not affiliated with or
supported by Simply Control. Please do not contact Simply Control about this
integration; report bugs and request support through the
[GitHub issue tracker](https://github.com/OttoHollmann/home-assistant-simplycore/issues).

## Installation

### HACS

Search for **SimplyCore** in HACS and install it.

Restart Home Assistant, then add **SimplyCore** from **Settings → Devices &
services → Add integration**. Enter the QR token and an optional display name.
Home Assistant installs the Socket.IO client dependency from the integration
manifest.

### Manual installation

Copy `custom_components/simplycore` into the `custom_components` directory of
your Home Assistant configuration, then restart Home Assistant and add the
integration as described above.

## Entities

The integration creates sensors for:

- Supply/exhaust airflow
- Supply, outside, and slot 1 temperatures
- Slot 1 CO₂, requested temperature, and active heating mode
- Unit condition and ventilation mode

It also creates binary sensors for unit power, actual boost activity, and
ventilation incoming-air heating (`incomingAirHeating`); this is not the hall's
central-heating valve. A separate **Central heating demand (estimated)**
binary sensor compares `requestedTemperature` with `temperatureSlot1` (the
configured exhaust-air sensor) and is on when the requested value is higher.
This estimates demand; the API does not report confirmed physical hall-valve
position. The ventilation selector displays `Normal`/`Vacation` (localized
using the unit's theme when available); the API value for Vacation remains
`minimal`. Temperature sliders select the active heating preset and the default
heating preset for normal and minimal ventilation. Their positions use the unit's configured preset temperatures
(observed as 17, 22, and 30 °C); they select the nearest preset and do not set
an arbitrary temperature.
Three boost buttons start bathroom, kitchen, or full-apartment
ventilation; each has its own active-state and remaining-time sensor. Labels
are taken from the unit's localized theme when available.
A schedule switch enables/disables the schedule without overwriting its events.
Each boost type also has a remaining-time sensor, updated every second from the
reported boost end time (or its start time and duration when no end time is
available). If the unit reports only that a boost is active and its duration,
the integration starts a local countdown when it first observes the active
state. The sensor reads `0` when the boost is inactive or its time has expired.

To configure custom weekly minimal-ventilation events, use the
`simplycore.set_schedule` action in **Developer Tools → Actions**. The action
form lets you choose a SimplyCore config entry and add multiple event rows.
Each event has a start and end time and a `day` number from 0 to 6. The service
normalizes times to `HH:MM` and passes day numbers through unchanged. The API
uses `1` for Monday and `2` for Tuesday. Submitting an empty event list clears
the configured events. For simplicity, use same-day events with an end time
later than the start time; this integration does not add cross-midnight handling.

Example service data:

```yaml
entry_id: YOUR_CONFIG_ENTRY_ID
enabled: true
events:
  - start: "08:00"
    end: "17:00"
    day: 1
  - start: "08:00"
    end: "17:00"
    day: 2
```

The action replaces the event list on the unit and sends it using
`unit.setSchedule`. Leave `enabled` unset to preserve the schedule's current
enabled state.

The setup form accepts the raw facility token, the QR URL
`https://air-link.simplycontrol.cz/<code>` (which redirects to
`https://air-link.simplycontrol.cz/?code=<token>`), or the sharing URL
`https://simplycore-link.simplycontrol.cz/code=...`. For the QR URL, the
integration follows the redirect and extracts the token before connecting.

Entity names and boost labels are localized for English, Czech, Danish, German,
Finnish, Hungarian, Italian, Polish, Spanish, and Swedish, matching the
languages reported in the unit's `localizedTheme` data. Ventilation mode
choices and room-specific boost labels use the unit's own localized theme.
Labels written directly into the example dashboard YAML remain English; change
those card labels manually if you want a translated dashboard.

## Known limitations

This integration was reverse-engineered and tested against one SimplyCore unit.
Other unit versions may use different command values or support additional
controls. If you have another unit and can help with testing, please open an
[issue](https://github.com/OttoHollmann/home-assistant-simplycore/issues); I can
investigate its compatibility and expand support.

On the tested unit, boost IDs `1` and `2` start the bathroom and kitchen boosts,
and `"full"` starts the full-apartment boost. These mappings may differ on other
units. Boost buttons only start boosts; no stop command is implemented.

The heating sliders select among the three fixed mode IDs (`1`–`3`), using the
temperatures reported for those presets. They do not set an arbitrary
temperature or change the configured preset temperatures. Other units may
support direct temperature setting, but this integration does not implement it
yet. If you have a unit that supports this feature and can help with testing,
please contact me through the
[GitHub issue tracker](https://github.com/OttoHollmann/home-assistant-simplycore/issues);
I can investigate adding support. There is no power-off command for the tested
unit, so power is reported as a sensor rather than controlled through a switch.

Commands are sent without requesting a Socket.IO acknowledgement. The
integration relies on subsequent server state updates and does not optimistically
change entity state; commands currently work on the tested unit. `boostEnabled`
indicates boost capability, not active boost state; active state follows the
individual `boosted*` fields.

## License

This project is distributed under the GNU General Public License v3.0. See
[LICENSE](./LICENSE) for the full text.
