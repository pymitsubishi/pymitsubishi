"""Read-only ATA telemetry with validated frames and explicit uncertainty.

Only decode replies already supplied by the adapter. Unknown commands and bytes
remain available as hexadecimal data; this module never generates requests.
Offsets below are relative to the 16-byte payload (command at offset zero).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import xml.etree.ElementTree as ET

REFERENCE = "https://muart-group.github.io/developer/it-protocol"


@dataclass(frozen=True)
class TelemetryField:
    group: int
    offsets: tuple[int, ...]
    confidence: str = "documented"
    unit: str | None = None


FIELD_INFO: dict[str, TelemetryField] = {}


def _fields(group: int, definitions: dict[str, tuple[Any, ...]]) -> None:
    for name, args in definitions.items():
        FIELD_INFO[name] = TelemetryField(group, *args)


_fields(
    2,
    {
        "power_on": ((3,),),
        "mode_code": ((4,),),
        "isee_active": ((4,),),
        "target_temperature": ((5, 11), "documented", "°C"),
        "requested_fan_code": ((6,),),
        "vertical_vane_code": ((7,),),
        "remote_lock_flags": ((8,),),
        "power_locked": ((8,),),
        "mode_locked": ((8,),),
        "temperature_locked": ((8,),),
        "horizontal_vane_code": ((10,),),
        "horizontal_vane_extra_flags": ((10,), "raw"),
        "dehumidifier_setting_raw": ((12,), "candidate"),
        "power_saving_raw": ((13,), "candidate"),
        "airflow_control_code": ((14,),),
        "left_vertical_vane_raw": ((15,), "candidate"),
    },
)
_fields(
    3,
    {
        "room_temperature_coarse": ((3,), "documented", "°C"),
        "outdoor_temperature": ((5,), "documented", "°C"),
        "room_temperature_fine": ((6,), "documented", "°C"),
        "inside_temperature_2": ((7,), "candidate", "°C"),
        "runtime_minutes": ((10, 11, 12, 13), "candidate", "min"),
    },
)
_fields(4, {"error_code": ((4, 5),), "error_display_code_raw": ((6,),), "error_display_code": ((6,), "candidate")})
_fields(
    5,
    {
        key: ((offset,), "candidate")
        for key, offset in [
            ("timer_mode_code", 3),
            ("timer_on_set_raw", 4),
            ("timer_off_set_raw", 5),
            ("timer_on_remaining_raw", 6),
            ("timer_off_remaining_raw", 7),
        ]
    },
)
_fields(
    6,
    {
        "compressor_frequency": ((3,), "documented", "Hz"),
        "operating": ((4,),),
        "input_watts": ((5, 6), "candidate", "W"),
        "energy_counter_100wh": ((7, 8), "candidate"),
    },
)
_fields(
    9,
    {
        "status_flags": ((3,),),
        "filter_reported": ((3,),),
        "defrost_reported": ((3,),),
        "preheat_reported": ((3,),),
        "standby_reported": ((3,),),
        "unknown_status_flags": ((3,), "raw"),
        "actual_fan_code": ((4,),),
        "auto_mode_raw": ((5,), "candidate"),
        "auto_mode_code": ((5,), "candidate"),
        "auto_leader_candidate": ((5,), "candidate"),
    },
)
_fields(
    0xC9,
    {
        **{
            name: ((offset,), "candidate")
            for name, offset in [
                ("capability_thermal_image", 6),
                ("capability_touch_flow", 6),
                ("capability_auto", 6),
                ("capability_heat_disabled", 7),
                ("capability_vertical_vane", 7),
                ("capability_swing", 7),
                ("capability_dry_disabled", 8),
                ("capability_fan_disabled", 8),
                ("capability_extended_temperature", 8),
                ("capability_auto_fan_disabled", 8),
                ("capability_installer_functions", 8),
                ("capability_test_mode", 8),
                ("capability_dry_temperature", 8),
                ("capability_status_display", 9),
                ("capability_outdoor_temperature", 9),
            ]
        },
        **{
            name: ((offset,), "candidate", "°C")
            for name, offset in [
                ("minimum_cool_temperature", 10),
                ("maximum_cool_temperature", 11),
                ("minimum_heat_temperature", 12),
                ("maximum_heat_temperature", 13),
                ("minimum_auto_temperature", 14),
                ("maximum_auto_temperature", 15),
            ]
        },
    },
)
_fields(
    0xC9,
    {
        "capability_fan_speed_code": ((7, 8, 9), "raw"),
        "capability_fan_speed_count": ((7, 8, 9), "candidate"),
    },
)
_fields(
    0xCD,
    {
        **{
            name: ((offset,), "candidate")
            for name, offset in [
                ("capability_dehumidify_percent", 7),
                ("capability_power_saving", 7),
                ("capability_remote_handle", 7),
                ("capability_effective_temperature", 7),
                ("capability_ventilation_assist", 8),
                ("capability_online_serial_writing", 13),
            ]
        },
        **{
            name: ((offset,), "candidate", "°C")
            for name, offset in [
                ("cd_minimum_cool_temperature", 1),
                ("cd_maximum_cool_temperature", 2),
                ("cd_minimum_heat_temperature", 3),
                ("cd_maximum_heat_temperature", 4),
                ("cd_minimum_auto_temperature", 5),
                ("cd_maximum_auto_temperature", 6),
            ]
        },
    },
)


@dataclass(frozen=True)
class TelemetryFrame:
    raw: str
    valid: bool
    reason: str
    service: int | None = None
    group: int | None = None
    payload: tuple[int, ...] = ()


@dataclass
class ATATelemetry:
    frames: list[TelemetryFrame] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)
    group_quality: dict[str, str] = field(default_factory=dict)
    unknown_bytes: dict[str, dict[str, int]] = field(default_factory=dict)

    def value(self, name: str) -> Any:
        """None means missing, unsupported, invalid or not safely interpreted."""
        return self.values.get(name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _frame(value: str) -> TelemetryFrame:
    try:
        data = bytes.fromhex(value)
    except (ValueError, TypeError):
        # No arbitrary strings (XML, identity or error bodies) in telemetry logs.
        return TelemetryFrame("", False, "invalid_hex")
    group = data[5] if len(data) > 5 else None
    service = data[1] if len(data) > 1 else None

    def invalid(reason: str) -> TelemetryFrame:
        return TelemetryFrame(data.hex(), False, reason, service, group)

    if len(data) < 7 or len(data) != data[4] + 6:
        return invalid("invalid_length")
    if data[0] != 0xFC or data[2:4] != b"\x01\x30" or service not in (0x62, 0x7B):
        return invalid("unsupported_protocol")
    if (-sum(data[1:-1])) & 255 != data[-1]:
        return invalid("invalid_checksum")
    if (group in (2, 3, 4, 5, 6, 9, 0xC9, 0xCD)) and data[4] != 16:
        return invalid("unexpected_payload_length")
    if (group in (0xC9, 0xCD) and service != 0x7B) or (group in (2, 3, 4, 5, 6, 9) and service != 0x62):
        return invalid("unexpected_service")
    return TelemetryFrame(data.hex(), True, "valid", service, group, tuple(data[5:-1]))


def _temperature(raw: int) -> float | None:
    return (raw - 0x80) / 2 if raw else None


def _decode(group: int, p: tuple[int, ...]) -> dict[str, Any]:
    if group == 2:
        return {
            "power_on": bool(p[3]) if p[3] in (0, 1) else None,
            "mode_code": p[4] & 7,
            "isee_active": bool(p[4] & 8),
            "target_temperature": _temperature(p[11]) if p[11] else 31 - p[5],
            "requested_fan_code": p[6],
            "vertical_vane_code": p[7],
            "remote_lock_flags": p[8],
            "power_locked": bool(p[8] & 1),
            "mode_locked": bool(p[8] & 2),
            "temperature_locked": bool(p[8] & 4),
            "horizontal_vane_code": p[10] & 15,
            "horizontal_vane_extra_flags": p[10] & 0xF0,
            "dehumidifier_setting_raw": p[12],
            "power_saving_raw": p[13],
            "airflow_control_code": p[14],
            "left_vertical_vane_raw": p[15],
        }
    if group == 3:
        return {
            "room_temperature_coarse": 10 + p[3],
            "outdoor_temperature": None if p[5] in (0, 1) else _temperature(p[5]),
            "room_temperature_fine": _temperature(p[6]),
            "inside_temperature_2": _temperature(p[7]),
            "runtime_minutes": int.from_bytes(bytes(p[10:14]), "big"),
        }
    if group == 4:
        lower = "0123456789ABCDEFOHJLPU"
        display = "AbEFJLPU"[(p[6] & 0xE0) >> 5] + lower[p[6] & 31] if p[6] & 31 < len(lower) else None
        return {
            "error_code": int.from_bytes(bytes(p[4:6]), "big"),
            "error_display_code_raw": p[6],
            "error_display_code": display,
        }
    if group == 5:
        return dict(
            zip(
                [
                    "timer_mode_code",
                    "timer_on_set_raw",
                    "timer_off_set_raw",
                    "timer_on_remaining_raw",
                    "timer_off_remaining_raw",
                ],
                p[3:8],
                strict=True,
            )
        )
    if group == 6:
        return {
            "compressor_frequency": p[3],
            "operating": bool(p[4]) if p[4] in (0, 1) else None,
            "input_watts": int.from_bytes(bytes(p[5:7]), "big"),
            "energy_counter_100wh": int.from_bytes(bytes(p[7:9]), "big"),
        }
    if group == 9:
        return {
            "status_flags": p[3],
            "filter_reported": bool(p[3] & 1),
            "defrost_reported": bool(p[3] & 2),
            "preheat_reported": bool(p[3] & 4),
            "standby_reported": bool(p[3] & 8),
            "unknown_status_flags": p[3] & 0xF0,
            "actual_fan_code": p[4],
            "auto_mode_raw": p[5],
            "auto_mode_code": p[5] & 0x3F,
            "auto_leader_candidate": bool(p[5] & 0x40),
        }
    if group == 0xC9:
        fields = [
            ("capability_thermal_image", 6, 8),
            ("capability_touch_flow", 6, 0x40),
            ("capability_auto", 6, 0x80),
            ("capability_heat_disabled", 7, 2),
            ("capability_vertical_vane", 7, 0x20),
            ("capability_swing", 7, 0x40),
            ("capability_dry_disabled", 8, 1),
            ("capability_fan_disabled", 8, 2),
            ("capability_extended_temperature", 8, 4),
            ("capability_auto_fan_disabled", 8, 0x10),
            ("capability_installer_functions", 8, 0x20),
            ("capability_test_mode", 8, 0x40),
            ("capability_dry_temperature", 8, 0x80),
            ("capability_status_display", 9, 1),
            ("capability_outdoor_temperature", 9, 0x20),
        ]
        result: dict[str, Any] = {name: bool(p[offset] & mask) for name, offset, mask in fields}
        limits = [
            "minimum_cool_temperature",
            "maximum_cool_temperature",
            "minimum_heat_temperature",
            "maximum_heat_temperature",
            "minimum_auto_temperature",
            "maximum_auto_temperature",
        ]
        result.update({name: _temperature(p[offset]) if p[8] & 4 else None for offset, name in enumerate(limits, 10)})
        fan_code = ((p[7] & 0x10) >> 2) | ((p[8] & 8) >> 2) | ((p[9] & 2) >> 1)
        result.update(
            capability_fan_speed_code=fan_code, capability_fan_speed_count={1: 1, 2: 2, 0: 3, 4: 4, 6: 5}.get(fan_code)
        )
        return result
    if group == 0xCD:
        result = {
            "capability_dehumidify_percent": bool(p[7] & 1),
            "capability_power_saving": bool(p[7] & 2) and not bool(p[7] & 0x20),
            "capability_remote_handle": bool(p[7] & 4),
            "capability_effective_temperature": bool(p[7] & 0x10),
            "capability_ventilation_assist": bool(p[8] & 0x40),
            "capability_online_serial_writing": bool(p[13] & 0x40),
        }
        limits = [
            "cd_minimum_cool_temperature",
            "cd_maximum_cool_temperature",
            "cd_minimum_heat_temperature",
            "cd_maximum_heat_temperature",
            "cd_minimum_auto_temperature",
            "cd_maximum_auto_temperature",
        ]
        result.update({name: _temperature(p[offset]) for offset, name in enumerate(limits, 1)})
        return result
    return {}


def parse_ata_telemetry(values: list[str]) -> ATATelemetry:
    """Preserve every supplied reply, but decode only valid nonconflicting groups."""
    result = ATATelemetry(frames=[_frame(value) for value in values])
    grouped: dict[int, list[TelemetryFrame]] = {}
    for frame in result.frames:
        if frame.group is not None:
            grouped.setdefault(frame.group, []).append(frame)
    for group, frames in grouped.items():
        key = f"0x{group:02X}"
        unique = {frame.raw for frame in frames}
        if any(not frame.valid for frame in frames):
            result.group_quality[key] = next(frame.reason for frame in frames if not frame.valid)
            continue
        if len(unique) > 1:
            result.group_quality[key] = "conflicting_replies"
            continue
        result.group_quality[key] = "valid"
        payload = frames[0].payload
        decoded = _decode(group, payload) if len(payload) == 16 else {}
        result.values.update(decoded)
        known = {0}
        for name in decoded:
            known.update(FIELD_INFO[name].offsets)
        result.unknown_bytes[key] = {str(i): value for i, value in enumerate(payload) if i not in known}
    return result


def parse_ata_response(response: str) -> ATATelemetry:
    try:
        root = ET.fromstring(response)
    except (ET.ParseError, TypeError):
        return ATATelemetry(group_quality={"response": "invalid_xml"})
    values = [e.text for e in root.findall(".//CODE/VALUE") if e.text]
    values.extend(e.text for e in root.findall(".//PROFILECODE//VALUE") if e.text)
    return parse_ata_telemetry(values)
