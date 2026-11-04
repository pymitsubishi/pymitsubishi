"""Read-only telemetry: unavailable values, unknown bytes and frame integrity."""

import dataclasses
from unittest.mock import MagicMock

import pytest

from pymitsubishi import MitsubishiController
from pymitsubishi.mitsubishi_telemetry import FIELD_INFO, parse_ata_response, parse_ata_telemetry


def frame(group, changes=None, service=0x62):
    payload = bytearray(16)
    payload[0] = group
    for offset, value in (changes or {}).items():
        payload[offset] = value
    packet = bytearray([0xFC, service, 1, 0x30, 16]) + payload
    packet.append((-sum(packet[1:])) & 255)
    return packet.hex()


def response(values, profiles=()):
    return (
        "<LSV><CODE>"
        + "".join("<VALUE>" + v + "</VALUE>" for v in values)
        + "</CODE><PROFILECODE>"
        + "".join("<VALUE>" + v + "</VALUE>" for v in profiles)
        + "</PROFILECODE></LSV>"
    )


def test_all_observed_groups_and_every_payload_byte_are_preserved():
    # Real off-state packet shapes; runtime and energy counters are synthetic.
    values = [
        frame(2, {4: 9, 5: 11, 7: 1, 11: 0xA8, 12: 40}),
        frame(3, {3: 7, 5: 1, 6: 0xA3, 7: 0xA3, 8: 0xFE, 9: 0x42}),
        frame(4, {4: 0x80}),
        frame(5),
        frame(6, {6: 1, 11: 0x42}),
        frame(9),
    ]
    snapshot = parse_ata_response(response(values))
    assert len(snapshot.frames) == 6
    assert all(f.valid for f in snapshot.frames)
    assert [f.raw for f in snapshot.frames] == values
    assert snapshot.value("compressor_frequency") == 0
    assert snapshot.value("error_display_code") == "A0"
    assert snapshot.value("outdoor_temperature") is None
    assert snapshot.value("room_temperature_fine") == 17.5
    assert snapshot.value("dehumidifier_setting_raw") == 40
    assert snapshot.value("target_temperature") == 20
    for f in snapshot.frames:
        represented = {0} | {int(i) for i in snapshot.unknown_bytes[f"0x{f.group:02X}"]}
        for key in snapshot.values:
            if FIELD_INFO[key].group == f.group:
                represented.update(FIELD_INFO[key].offsets)
        assert represented == set(range(16))


@pytest.mark.parametrize("flags", [0, 1, 2, 4, 8, 15, 0x82])
def test_status_flags_and_unknown_bits(flags):
    snapshot = parse_ata_telemetry([frame(9, {3: flags, 4: 6, 5: 0x42})])
    assert snapshot.value("defrost_reported") is bool(flags & 2)
    assert snapshot.value("unknown_status_flags") == flags & 0xF0
    assert snapshot.value("actual_fan_code") == 6
    assert snapshot.value("auto_mode_raw") == 0x42
    assert snapshot.value("auto_mode_code") == 2
    assert snapshot.value("auto_leader_candidate") is True


def test_frequency_and_timer_bytes_are_not_assigned_invented_units():
    s = parse_ata_telemetry([frame(6, {3: 57, 4: 1, 5: 3, 6: 0xE8}), frame(5, {3: 3, 4: 6, 5: 12, 6: 2, 7: 8})])
    assert s.value("compressor_frequency") == 57
    assert s.value("input_watts") == 1000
    assert s.value("operating") is True
    assert s.value("timer_on_set_raw") == 6
    assert FIELD_INFO["timer_on_set_raw"].unit is None
    assert FIELD_INFO["timer_on_set_raw"].confidence == "candidate"


def test_remote_locks_and_display_error_out_of_range():
    s = parse_ata_telemetry([frame(2, {8: 5}), frame(4, {4: 0x80, 6: 0x1F})])
    assert s.value("power_locked") is True
    assert s.value("mode_locked") is False
    assert s.value("temperature_locked") is True
    assert s.value("error_display_code_raw") == 0x1F
    assert s.value("error_display_code") is None


def test_optional_capabilities_are_separate_from_live_status():
    profile = frame(0xC9, {8: 4, 9: 0x20, 10: 0xA0, 11: 0xBE, 12: 0x94, 13: 0xBE, 14: 0xA0, 15: 0xBE}, 0x7B)
    s = parse_ata_response(response([frame(9)], [profile]))
    assert s.value("capability_outdoor_temperature") is True
    assert s.value("minimum_cool_temperature") == 16
    assert s.value("minimum_heat_temperature") == 10
    assert s.value("maximum_heat_temperature") == 31
    assert s.value("defrost_reported") is False
    assert parse_ata_telemetry([frame(0xC9, service=0x7B)]).value("minimum_heat_temperature") is None


def test_missing_response_never_reuses_previous_true():
    assert parse_ata_telemetry([frame(9, {3: 2})]).value("defrost_reported") is True
    assert parse_ata_telemetry([]).value("defrost_reported") is None


def test_cd_candidate_capabilities_and_unknown_fan_combination():
    cd = frame(0xCD, {1: 0xA0, 2: 0xBE, 7: 0x13, 8: 0x40, 13: 0x40}, 0x7B)
    s = parse_ata_telemetry([cd, frame(0xC9, {9: 2}, 0x7B)])
    assert s.value("capability_power_saving") is True
    assert s.value("capability_effective_temperature") is True
    assert s.value("capability_ventilation_assist") is True
    assert s.value("cd_minimum_cool_temperature") == 16
    assert s.value("capability_fan_speed_code") == 1
    assert s.value("capability_fan_speed_count") == 1
    assert FIELD_INFO["cd_minimum_cool_temperature"].confidence == "candidate"
    assert parse_ata_telemetry([frame(0xCD, {7: 0x22}, 0x7B)]).value("capability_power_saving") is False
    assert parse_ata_telemetry([frame(0xC9, {7: 0x10, 8: 8, 9: 2}, 0x7B)]).value("capability_fan_speed_count") is None


def test_controller_includes_existing_profile_without_requesting_it():
    api = MagicMock()
    api.send_status_request.return_value = response([frame(9)], [frame(0xCD, {7: 0x10}, 0x7B)])
    state = MitsubishiController(api).fetch_status()
    assert state.ata_telemetry.value("capability_effective_temperature") is True
    api.send_status_request.assert_called_once_with(connect=None)


def test_conflicting_duplicate_or_invalid_packet_does_not_decode_false():
    good = frame(9, {3: 2})
    bad = good[:-2] + "00"
    for values in [[good, frame(9)], [bad], [good, bad], [good[:-2]]]:
        snapshot = parse_ata_telemetry(values)
        assert snapshot.value("defrost_reported") is None
        assert snapshot.group_quality["0x09"] != "valid"
    assert parse_ata_telemetry([good, good]).value("defrost_reported") is True


def test_unknown_group_preserved_without_interpretation():
    raw = frame(0xE1, {3: 99, 15: 240})
    s = parse_ata_telemetry([raw])
    assert s.values == {}
    assert s.frames[0].raw == raw
    assert s.unknown_bytes["0xE1"]["3"] == 99
    assert s.unknown_bytes["0xE1"]["15"] == 240


@pytest.mark.parametrize("values", [["not hex"], [None], ["00"], ["fc62027a10090000000000000000000000000000000a"]])
def test_bad_or_non_ata_frames_are_not_interpreted(values):
    s = parse_ata_telemetry(values)
    assert not s.values
    assert not any(f.valid for f in s.frames)


def test_xml_metadata_and_secrets_are_not_in_telemetry():
    xml = (
        "<LSV><MAC>private-mac</MAC><PASSWORD>private-secret</PASSWORD><CODE><VALUE>"
        + frame(9)
        + "</VALUE></CODE></LSV>"
    )
    snapshot = parse_ata_response(xml)
    assert "private" not in str(dataclasses.asdict(snapshot))
    assert parse_ata_response("<bad>").group_quality["response"] == "invalid_xml"


def test_controller_adds_telemetry_without_more_requests_or_commands():
    xml = response([frame(9, {3: 2, 4: 3})])
    api = MagicMock()
    api.send_status_request.return_value = xml
    controller = MitsubishiController(api)
    state = controller.fetch_status()
    assert state.ata_telemetry.value("defrost_reported") is True
    api.send_status_request.assert_called_once_with(connect=None)
    api.make_request.assert_not_called()
