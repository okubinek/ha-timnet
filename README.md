# TimNet for Home Assistant

Custom HACS integration for **Timpex TimNet 100 / 200** combustion controllers via **Modbus TCP**
([protocol description v2.1](https://timpex.cz/wp-content/uploads/2026/04/modbus_timnet_100a200.pdf)).

## Features

| Feature | TimNet 100 | TimNet 200 |
|---------|:----------:|:----------:|
| Temperature T1 (flue) | yes | yes |
| Temperature T2 | — | yes |
| Relay 1 / 2 status | — | yes (read-only) |
| Burn duration, damper, status, colour, faults | yes | yes |
| Door + SDS active | yes | yes |
| Start burning button / service | yes | yes |
| Acoustic signalling, mode / fuel / reload / SDS | yes | yes |

- Local polling (default every 5 s; device closes idle TCP after 10 s)
- Temperature specials: LO / HI / --- / inactive
- Optional custom names for T2 and relays (TimNet 200)
- Czech and English UI strings
- Diagnostics support

> Relays are **status-only**. The Modbus write map for 100/200 does not expose relay control — the firmware drives them (pump, HRV, hood, etc.).

## Install

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories
2. Add this repository as **Integration**
3. Install **TimNet**, restart Home Assistant
4. Settings → Devices & services → Add → **TimNet**

### Manual

Copy `custom_components/timnet` into your HA `config/custom_components/` folder and restart.

## Configuration

| Field | Default | Notes |
|-------|---------|-------|
| Name | TimNet | Device name in HA |
| Host | — | Unit IP on your LAN |
| Port | 502 | Modbus TCP |
| Unit ID | 1 | Copied by the unit (addressing is by IP) |
| Model | TimNet 100 | Choose **TimNet 200** for T2 + relays |
| Scan interval | 5 s | Max 10 s |

You can change host / port / model later via **Reconfigure**, or adjust poll interval and custom entity names under **Configure**.

### Wi‑Fi / Modbus prerequisites

- The smart-home Modbus module is a **paid option** from Timpex — request it when ordering or via support.
- First join the unit’s AP (`TIMPEX_…`, password `1234567890`) and open `http://192.168.2.1` to attach it to your 2.4 GHz Wi‑Fi. Official steps: [timpex.cz/podpora](https://timpex.cz/podpora/).
- Use **one** Modbus TCP client toward the unit (disable any YAML Modbus hub for the same IP).

## Start burning

- UI: device page → **Start burning** / **Start hoření**
- Service: `timnet.start_regulation`
- Automation: call the button entity or the service

Writes holding register `0 = 1` (START) per TimNet Modbus TCP v2.1.

## Supported models

| Series | Status | Official Modbus PDF |
|--------|--------|---------------------|
| TimNet 100 / 200 | Supported | [modbus_timnet_100a200.pdf](https://timpex.cz/wp-content/uploads/2026/04/modbus_timnet_100a200.pdf) |
| TimNet 250 / 300 / 400 / 500 | Not yet (different register map) | [modbus_timnet_250az500.pdf](https://timpex.cz/wp-content/uploads/2026/06/modbus_timnet_250az500.pdf) |
| ECO / SMART / REG | Not supported (no public Modbus map for this integration) | — |

## Public repository checklist (HACS default)

If you want this repo listed as a default HACS integration:

- [x] `brand/icon.png` (+ `@2x`) at repository root
- [x] Valid `manifest.json` (`domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, `version`)
- [x] `hacs.json` with minimum Home Assistant version
- [ ] GitHub Actions: HACS Action + hassfest (see `.github/workflows/validate.yml`)
- [ ] Repository description, topics (`homeassistant`, `hacs`, `timnet`, `modbus`, `timpex`), issues enabled
- [ ] Publish a **GitHub Release** (not only a git tag) after CI is green

## Licence

MIT — see [LICENSE](LICENSE).

TimNet / Timpex are trademarks of Timpex spol. s r.o. This project is an unofficial community integration.
