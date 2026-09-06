"""Constants for the TimNet combustion control integration.

Register map per TimNet MODBUS TCP v2.1 (TimNet 100/200, decimal 0000–0015).
"""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "timnet"
MANUFACTURER = "Timpex"
MODEL_100 = "TimNet 100"
MODEL_200 = "TimNet 200"
MODELS = (MODEL_100, MODEL_200)
DEFAULT_NAME = "TimNet"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
# Device closes TCP if idle >10 s (manual §1.1.2)
DEFAULT_SCAN_INTERVAL = 5

CONF_MODEL = "model"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_T2_NAME = "t2_name"
CONF_RELAY1_NAME = "relay1_name"
CONF_RELAY2_NAME = "relay2_name"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BUTTON,
]

# --- Read holding registers (0x03 / 0x04) — TimNet 100/200 ---
REG_TT = 0  # T1 temperature ×10
REG_TT2 = 1  # T2 (TimNet 200 only)
REG_CAS = 2  # burn duration seconds
REG_SER1 = 3  # damper position %
REG_INP = 4  # door switch
REG_REZIM = 5  # burn mode
REG_PALIVO = 6  # fuel type
REG_PRILOZ = 7  # reload offset
REG_SDS = 8  # SDS sensitivity
REG_BARVA = 9  # temperature colour
REG_BEEP_R = 10  # beep state (read)
REG_RELE1 = 11  # TimNet 200
REG_RELE2 = 12  # TimNet 200
REG_PORUCHA = 13  # fault bitmask
REG_STAT = 14  # unit status
REG_P_LIFE = 15  # total reloads

READ_START = REG_TT
READ_COUNT = 16  # registers 0–15

# --- Write holding registers (0x06 / 0x10) ---
REG_START_W = 0
REG_BEEP_W = 1
REG_REZIM_W = 2
REG_PALIVO_W = 3
REG_PRILOZ_W = 4
REG_SDS_W = 5

WRITE_START = 1
WRITE_BEEP_ON = 15
WRITE_BEEP_OFF = 255
WRITE_SDS_OFF = 255

# Temperature specials (before ÷10)
TEMP_LO = -20000
TEMP_HI = 20000
TEMP_UNMEASURED = 20001
TEMP_INACTIVE = 20002
TEMP_SPECIALS = {TEMP_LO, TEMP_HI, TEMP_UNMEASURED, TEMP_INACTIVE}

TEMP_SPECIAL_LABELS = {
    TEMP_LO: "LO",
    TEMP_HI: "HI",
    TEMP_UNMEASURED: "---",
    TEMP_INACTIVE: "inactive",
}

DOOR_OPEN = 255
DAMPER_INIT = 255
RELAY_ON = 1

STATUS_MAP = {
    0: "power_start",
    1: "idle_100",
    2: "idle_0",
    3: "lighting",
    4: "start_regulation",
    5: "burning_rising",
    6: "burning_falling",
    7: "reload",
    8: "ember",
    10: "not_lit",
    13: "overheated",
    14: "door_open_long",
    15: "test_mode",
    20: "temp_fault",
}

MODE_MAP = {1: "eco", 2: "standard", 3: "turbo"}
MODE_WRITE = {"eco": 1, "standard": 2, "turbo": 3}

FUEL_MAP = {1: "wood", 2: "briquettes"}
FUEL_WRITE = {"wood": 1, "briquettes": 2}

RELOAD_MAP = {1: "m2", 2: "m1", 3: "standard", 4: "p1", 5: "p2"}
RELOAD_WRITE = {"m2": 1, "m1": 2, "standard": 3, "p1": 4, "p2": 5}

COLOUR_MAP = {
    0: "none",
    1: "yellow",
    2: "green",
    3: "red",
}

SDS_SENSITIVITY_MAP = {1: "m2", 2: "m1", 3: "standard", 4: "p1", 5: "p2"}
SDS_WRITE = {"m2": 1, "m1": 2, "standard": 3, "p1": 4, "p2": 5, "off": 255}

SERVICE_START_REGULATION = "start_regulation"


def model_supports_t2(model: str) -> bool:
    """Return True if the model exposes T2 / relays."""
    return model == MODEL_200
