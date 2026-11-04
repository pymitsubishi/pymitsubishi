# Read-only ATA telemetry

`ParsedDeviceState.ata_telemetry` contains an additive snapshot of ATA replies
already present in the adapter response. Existing parsed fields and control
methods retain their behavior. No new queries or CONNECT changes are required.

```python
state = controller.fetch_status()
snapshot = state.ata_telemetry
if snapshot is not None:
    defrost = snapshot.value("defrost_reported")  # bool or None
    frequency = snapshot.value("compressor_frequency")  # reported Hz or None
    evidence = snapshot.to_dict()  # JSON-compatible raw/decoded snapshot
```

The public helpers `parse_ata_telemetry(list_of_hex_frames)` and
`parse_ata_response(xml_response)` can also decode offline captures. Only CODE
and PROFILECODE values are retained, excluding XML identities and credentials.
Full frames may still contain model-dependent unknown data; review captures
before sharing them publicly.

## Coverage and interpretation

| Group | Added interpretation |
| --- | --- |
| `0x02` | Settings, remote-lock mask and bits, additional vane flags, raw dehumidifier/power-saving/airflow values |
| `0x03` | Temperature encodings, unavailable outdoor sentinels, candidate second temperature and runtime |
| `0x04` | Numeric error and raw/candidate display code; `A0` is all clear, not a fault |
| `0x05` | Timer mode and four raw timer bytes, without unverified time units |
| `0x06` | Reported compressor frequency, operating bit and candidate electrical counters |
| `0x09` | Filter, defrost, preheat and standby bits; actual fan code; raw/candidate auto-mode fields |
| `0xC9` | Candidate capability flags, fan-speed count and temperature bounds |
| `0xCD` | Candidate capabilities and possible alternative setpoint bounds |
| Other replies | Complete frame, payload and unknown bytes, without guessed meanings |

`FIELD_INFO` describes the group, payload offsets, units and confidence of each
field: `documented`, `candidate`, or `raw`. Documented means described by the
community protocol reference, not verified by Mitsubishi or supported by every
unit. Missing/unsupported values return `None`; zero alone does not establish
hardware support. Do not infer delivered heat, airflow or COP from these fields.
Indoor temperature 2 is not established as coil or discharge-air temperature.

The parser checks the service, ATA header, declared length and checksum. Known
groups need a 16-byte payload. Invalid or conflicting replies retain evidence
and quality but publish no interpreted values for that group. Duplicate identical
replies are accepted. Each snapshot is rebuilt, so missing data cannot reuse an
earlier true status. Consumers must also check their transport/coordinator's
refresh success and freshness.

Status bits represent reports from each indoor unit. Heads on the same outdoor
unit must not have defrost counts, compressor frequencies or power readings
summed as independent machines. A flag cycle needs physical validation before
being used for automated heating decisions.

References: [protocol](https://muart-group.github.io/developer/it-protocol),
[run status](https://muart-group.github.io/developer/it-protocol/0x62-get-response/0x09-get-run-state),
[capabilities](https://muart-group.github.io/developer/it-protocol/0x7B-identify-response/0xC9-base-capabilities),
[CD candidate capabilities](https://muart-group.github.io/developer/it-protocol/0x7B-identify-response/0xCD-unknown-identify-packet).
