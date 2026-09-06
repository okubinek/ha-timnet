"""Unit tests for TimNet value decoding (no live device / HA install)."""

from __future__ import annotations

TEMP_LO = -20000
TEMP_HI = 20000
TEMP_UNMEASURED = 20001
TEMP_INACTIVE = 20002
TEMP_SPECIAL_LABELS = {
    TEMP_LO: "LO",
    TEMP_HI: "HI",
    TEMP_UNMEASURED: "---",
    TEMP_INACTIVE: "inactive",
}
MODEL_100 = "TimNet 100"
MODEL_200 = "TimNet 200"


def decode_temp(raw: int | None) -> float | str | None:
    if raw is None:
        return None
    if raw in TEMP_SPECIAL_LABELS:
        return TEMP_SPECIAL_LABELS[raw]
    return round(raw * 0.1, 1)


def decode_sds(code: int) -> str:
    if code == 255:
        return "off"
    sens = code // 10
    active = code % 10
    base = {1: "m2", 2: "m1", 3: "standard", 4: "p1", 5: "p2"}.get(sens, "unknown")
    suffix = "active" if active == 1 else "inactive"
    return f"{base}_{suffix}"


def decode_fault(code: int) -> str:
    if code == 0:
        return "none"
    parts: list[str] = []
    if code & 1:
        parts.append("t1")
    if code & 2:
        parts.append("t2")
    if code & 8:
        parts.append("door")
    return "_".join(parts) if parts else f"code_{code}"


def model_supports_t2(model: str) -> bool:
    return model == MODEL_200


def test_temperature_numeric() -> None:
    assert decode_temp(255) == 25.5
    assert decode_temp(-50) == -5.0


def test_temperature_specials() -> None:
    assert decode_temp(TEMP_LO) == "LO"
    assert decode_temp(TEMP_HI) == "HI"
    assert decode_temp(TEMP_UNMEASURED) == "---"
    assert decode_temp(TEMP_INACTIVE) == "inactive"


def test_sds_composite() -> None:
    assert decode_sds(255) == "off"
    assert decode_sds(31) == "standard_active"
    assert decode_sds(30) == "standard_inactive"
    assert decode_sds(11) == "m2_active"


def test_fault_bitmask() -> None:
    assert decode_fault(0) == "none"
    assert decode_fault(1) == "t1"
    assert decode_fault(2) == "t2"
    assert decode_fault(8) == "door"
    assert decode_fault(9) == "t1_door"
    assert decode_fault(3) == "t1_t2"


def test_model_profile() -> None:
    assert model_supports_t2(MODEL_200) is True
    assert model_supports_t2(MODEL_100) is False


if __name__ == "__main__":
    test_temperature_numeric()
    test_temperature_specials()
    test_sds_composite()
    test_fault_bitmask()
    test_model_profile()
    print("ok")
