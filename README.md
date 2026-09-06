# TimNet for Home Assistant

Custom integration for **TimNet 100** combustion controllers via **Modbus TCP** (protocol description v2.1).

## Features

- Local polling (default every 5 s; device closes idle TCP after 10 s)
- Temperature T1 with LO / HI / --- / inactive handling
- Status, door, mode, fuel, SDS, colour, faults, damper, burn time
- **Start burning** button + `timnet.start_regulation` service
- Acoustic signalling switch, selects for mode / fuel / reload offset / SDS

## Install

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories
2. Add this repository as **Integration**
3. Install **TimNet**, restart Home Assistant
4. Settings → Devices & services → Add → **TimNet**

### Manual

Copy `custom_components/timnet` into your HA `config/custom_components/` folder and restart.

## Configuration

| Field | Default |
|-------|---------|
| Host | (your TimNet IP) |
| Port | 502 |
| Unit ID | 1 |
| Scan interval | 5 s (max 10) |

## Start burning

- UI: device page → **Start hoření** / **Start burning**
- Service: `timnet.start_regulation`
- Automation: call the button entity or the service

Writes holding register `0 = 1` (START) per TimNet Modbus TCP v2.1.

## Notes

- Use **one** Modbus TCP client toward the unit (disable YAML Modbus hub for the same IP).
- TimNet 200 (T2 / relays) is not exposed yet.

## Licence

MIT
