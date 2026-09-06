# Changelog

## 0.2.0

### Added

- TimNet 200 support: temperature T2 and read-only relay 1 / 2 status
- Model selection in config flow, options, and reconfigure
- Optional custom names for T2 and relays
- Binary sensors for door, SDS active, and relays (200)
- Brand icons for HACS / Home Assistant (`brand/` and `custom_components/timnet/brand/`)
- Dynamic / state icons via `icons.json`
- Config entry migration to version 2 (default model TimNet 100)
- Czech/English strings for new entities, options, reconfigure, and services

### Changed

- Manufacturer shown as **Timpex**
- Duplicate read-only sensors (mode / fuel / reload / SDS) disabled by default — use selects to control
- Door moved from enum sensor to binary sensor
- Minimum Home Assistant version raised to 2024.4.0 (reconfigure flow)

### Docs

- README covers 100 vs 200, Wi‑Fi/Modbus notes, and TimNet 250–500 as future work

## 0.1.0

- Initial TimNet 100 Modbus TCP integration
