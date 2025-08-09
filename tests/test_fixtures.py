"""
Test fixtures containing sanitized real device responses for testing.

All personal information (MAC address, serial number) has been anonymized.
"""

# Real device response with sanitized MAC and serial
REAL_DEVICE_XML_RESPONSE = """<LSV><MAC>AA:BB:CC:DD:EE:FF</MAC><SERIAL>1234567890</SERIAL><CONNECTION>NOT OK</CONNECTION><VERSION>V5.2.7</VERSION><STATUS>OK</STATUS><PROFILECODE><DATA><VALUE>0300200714070000000000000000000000000000000000000000000000000000</VALUE></DATA></PROFILECODE><CODE><DATA><VALUE>ffffffffffffffffffff0202008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0302008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0402008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0502008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0602008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0702008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0802008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0902008000</VALUE></DATA></CODE><CODE><DATA><VALUE>ffffffffffffffffffff0a02008000</VALUE></DATA></CODE><PROFILECODE><DATA><VALUE>a0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0be</VALUE></DATA></PROFILECODE><PROFILECODE><DATA><VALUE>0000000000000000000000000000000000000000000000000000000000000000</VALUE></DATA></PROFILECODE><PROFILECODE><DATA><VALUE>0000000000000000000000000000000000000000000000000000000000000000</VALUE></DATA></PROFILECODE><PROFILECODE><DATA><VALUE>0000000000000000000000000000000000000000000000000000000000000000</VALUE></DATA></PROFILECODE><LED><LED1>1:30,0:30</LED1><LED2>1:30,0:30</LED2><LED3>1:30,0:30</LED3><LED4>1:5,0:45</LED4></LED><ECHONET>ON</ECHONET></LSV>"""

# Expected parsed device state from the above XML
EXPECTED_DEVICE_STATE = {
    "device_info": {"mac": "AA:BB:CC:DD:EE:FF", "serial": "1234567890", "rssi": "", "app_version": ""},
    "general_states": {
        "power": "ON",
        "mode": "COOLER",
        "target_temperature_celsius": 22.5,
        "fan_speed": "AUTO",
        "vertical_wind_direction_right": "V1",
        "vertical_wind_direction_left": "AUTO",
        "horizontal_wind_direction": "R",
        "dehumidification_setting": 70,
        "power_saving_mode": False,
        "wind_and_wind_break_direct": 0,
    },
    "sensor_states": {
        "room_temperature_celsius": 22.0,
        "outside_temperature_celsius": 20.0,
        "thermal_sensor_active": False,
        "wind_speed_pr557": 0,
    },
    "error_states": {"abnormal_state": False, "error_code": "8000"},
}

# Sample encrypted ESV request/response for API tests
SAMPLE_ESV_REQUEST = """<?xml version="1.0" encoding="UTF-8"?><ESV>98M+S/NAN/HbftgkKhWBuPwFQoNq6AseKt38ZYh2tOWewRpmPA8CgCn1tOm5/Ek1</ESV>"""

SAMPLE_ESV_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?><ESV>98M+S/NAN/HbftgkKhWBuMGx0iKyuKuBLr7G3hhe4qOz8qNkqhqs1AmgHX4By6m2iiT95TKT2tHmNXlbp7cDrP+zAfduEqdSSU0yp6Ma3cM4kXvjn0GJt22oq3GnA+DvSyo2GYlIUQXWqQwe/BYDdTqKbKzj9rlCxGMGsjKu2pZxzsjQ4zq49SiKRi5+tVSBlxkVG20wNg7e3LCoWbn6qjypoEiAhBzW7voa9UYk+GwOWY4q6YcYKMGYIqKJ/I/Plk754XRTmutol4OrtEs3zqJ08xjcD/cUx6QtgnBI7IIA0RLz0+T8DYu6ODXCGKcwG/dEWrtlZBDDombzYltsulECx/g4n4/zMqzYlhKhV1FmDHvMeDVT0AvBvad2xHII+uJjNGvcO7lbjwtu34hxKF05dV2YS/x2DYxm7eUcgyG/VKoPZamynVpzKYPV3uSsUESCze2vQ6+J6H8d6Mt1qxuGo27gSMRQVcNsuqsAkQXtj7ZJor3cZetaf+yDFUjkaZYlBVsJMJnohifxBJRUo6O11QYQVxvv6SAaS/I4dZmPYd3ZGzWMBRN/kEvVCbYDSUPY+XyvAWf6tPxnv1Lel1Kuhx1yjoUI7D29r29dwm9Uhurf8X8706yGn26qCAwRPY7J+I7WrDXnILYVGKXk7o/7wgUnnq0nrc/g8B3xs7kQrIu4/cJjUqu+W9eoMvBsEP4wUAFC3G8Yi9NjCgUCqpRqnxDx3iNgJzqgp9ynU9F8BbVQJSOmggJ5l2xKi8w5uvmFd+q61JEAQRS2EdWwVDSo/WnH148LAWIoUWaXgPz+7S7Ar3DJbJTm5bOmLvnQ1P2owOcEeDpru+eMHA3D0jNN2cOFYXfnigAG8xSrmcPe0PzWtEHwf2IEBs4h/h61Wq3DJ8wx0A6E2xFpBN1JwetLxDPJmU5MlbNmHdS265w6NNfcqq+/sI/Bm9+BNs8PVWWDQuaICVEftzTBejQwzZotLTjqw/iENEZCOSMIevfgH9mmbmrcIjLSannZFjSM3DQiVS3dIrpDSyZbyEJsAPXkCidsy0EZQGUFmfohx5eYnENTltP0bbtF3UwT93nAttHBVqQL9jFx5Qe+YBEnh2ADlwI9iHmivPVPy+BC1qSpPOXBWqETvx2SXJMX4Qqc9o8Rb0GayS2PRaSLEmlE/2Pm7cy8tw+4O/MW8x+SzheHly1eVQuDE4IxNv60gGJk6yOofjhsdNvhHvO6eqdxuC92us3Jd1rG833RDBHevy6E49K/K4QDYmkhmTgUHU0s/qgLVR2745AqOTr61q4l+cYkAfCvoKrh8ABA6Z0PXLSBKVRvfJRa6O8yh+81PiEFuSauGM8zkJN2Ghg2GtU7lTJIkCgCEp3TAzKLpwGuZ9Y=</ESV>"""

# Profile codes found in real device responses
SAMPLE_PROFILE_CODES = [
    "0300200714070000000000000000000000000000000000000000000000000000",  # First profile with capability flags
    "a0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0be",  # Second profile with repeated pattern
    "0000000000000000000000000000000000000000000000000000000000000000",  # Empty profile codes
]

# Sample hex code values for parser testing
SAMPLE_CODE_VALUES = [
    "ffffffffffffffffffff0202008000",  # Group code 02
    "ffffffffffffffffffff0302008000",  # Group code 03
    "ffffffffffffffffffff0402008000",  # Group code 04
    "ffffffffffffffffffff0502008000",  # Group code 05
    "ffffffffffffffffffff0602008000",  # Group code 06
    "ffffffffffffffffffff0702008000",  # Group code 07
    "ffffffffffffffffffff0802008000",  # Group code 08
    "ffffffffffffffffffff0902008000",  # Group code 09
    "ffffffffffffffffffff0a02008000",  # Group code 0a
]

# Expected capability analysis results
EXPECTED_CAPABILITIES = {
    "supported_group_codes": {"02", "03", "04", "05", "06", "07", "08", "09", "0a"},
    "profile_codes": {
        "profile_0": "0300200714070000000000000000000000000000000000000000000000000000",
        "profile_1": "a0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0bea0be",
        "profile_2": "0000000000000000000000000000000000000000000000000000000000000000",
        "profile_3": "0000000000000000000000000000000000000000000000000000000000000000",
        "profile_4": "0000000000000000000000000000000000000000000000000000000000000000",
    },
}

# Temperature control test cases
TEMPERATURE_TEST_CASES = [
    {"celsius": 16.0, "expected_units": 160, "valid": True},
    {"celsius": 22.5, "expected_units": 225, "valid": True},
    {"celsius": 25.0, "expected_units": 250, "valid": True},
    {"celsius": 32.0, "expected_units": 320, "valid": True},
    {"celsius": 15.9, "expected_units": None, "valid": False},  # Too low
    {"celsius": 32.1, "expected_units": None, "valid": False},  # Too high
]

# Mode control test cases
MODE_TEST_CASES = [
    {"mode": "COOLER", "hex_value": "03"},
    {"mode": "HEATER", "hex_value": "01"},
    {"mode": "AUTO", "hex_value": "08"},
    {"mode": "DEHUM", "hex_value": "02"},
    {"mode": "FAN", "hex_value": "07"},
]

# Device status summary expected format
EXPECTED_STATUS_SUMMARY = {
    "mac": "AA:BB:CC:DD:EE:FF",
    "serial": "1234567890",
    "power": "ON",
    "mode": "COOLER",
    "target_temp": 22.5,
    "fan_speed": "AUTO",
    "dehumidifier_setting": 70,
    "power_saving_mode": False,
    "room_temp": 22.0,
    "outside_temp": 20.0,
    "error_code": "8000",
    "abnormal_state": False,
}

# LED status patterns from real device
LED_PATTERNS = {"LED1": "1:30,0:30", "LED2": "1:30,0:30", "LED3": "1:30,0:30", "LED4": "1:5,0:45"}

# Error scenarios for testing
ERROR_TEST_CASES = [
    {"description": "Invalid IP address", "ip": "999.999.999.999", "expected_error": "connection"},
    {"description": "Timeout scenario", "ip": "192.168.1.254", "expected_error": "timeout"},
    {"description": "Invalid temperature", "temp": 50.0, "expected_error": "range"},
]
