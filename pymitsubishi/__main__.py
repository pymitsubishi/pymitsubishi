import argparse
import logging
from pprint import pprint
import time

from .mitsubishi_controller import MitsubishiController
from .mitsubishi_parser import (
    DriveMode,
    HorizontalWindDirection,
    VerticalWindDirection,
    WindSpeed,
    Controls,
    PowerOnOff,
    Controls08,
)

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--verbose", "-v", help="More verbose output (up to 2 times)", action="count", default=0)
parser.add_argument("host", help="Hostname or IP address to connect to, optionally followed by ':port'")
parser.add_argument("--reboot", help="Request the device to reboot", action="store_true")
parser.add_argument("--power", help="Set power", type=lambda s: s.upper(), choices=["ON", "OFF"])
parser.add_argument("--mode", help="Set operating mode", type=lambda s: s.upper(), choices=[_.name for _ in DriveMode])
parser.add_argument("--target-temperature", help="Set target temperature", type=float)
parser.add_argument("--fan-speed", help="Set fan speed", type=lambda s: s.upper(), choices=[_.name for _ in WindSpeed])
parser.add_argument(
    "--vertical-wind-direction",
    help="Set vertical vane position",
    type=lambda s: s.upper(),
    choices=[_.name for _ in VerticalWindDirection],
)
parser.add_argument(
    "--horizontal-wind-direction",
    help="Set horizontal vane position",
    type=lambda s: s.upper(),
    choices=[_.name for _ in HorizontalWindDirection],
)
parser.add_argument("--power-saving", help="Set power saving", type=lambda s: s.upper(), choices=["ON", "OFF"])
args = parser.parse_args()

logging.basicConfig(level=logging.WARNING - 10 * args.verbose)
logger = logging.getLogger(__name__)

ctrl = MitsubishiController.create(args.host)

ctrl.fetch_status()
desired_state = ctrl.state.general
controls = Controls.NoControl
controls08 = Controls08.NoControl

if args.mode:
    drive_mode = DriveMode[args.mode.upper()]
    print(f"Setting mode to {drive_mode}")
    if drive_mode == DriveMode.AUTO:
        drive_mode = 8
    else:
        drive_mode = drive_mode.value
    desired_state.drive_mode = drive_mode
    controls |= Controls.DriveMode
if args.target_temperature:
    print(f"Setting target temperature to {args.target_temperature}")
    desired_state.temperature = args.target_temperature
    controls |= Controls.Temperature
if args.fan_speed:
    fan_speed = WindSpeed[args.fan_speed.upper()]
    print(f"Setting fan speed to {fan_speed}")
    desired_state.wind_speed = fan_speed
    controls |= Controls.WindSpeed
if args.vertical_wind_direction:
    v_vane = VerticalWindDirection[args.vertical_wind_direction.upper()]
    print(f"Setting vertical wind direction to {v_vane}")
    desired_state.vertical_wind_direction = v_vane
    controls |= Controls.UpDownWindDirection
if args.horizontal_wind_direction:
    h_vane = HorizontalWindDirection[args.horizontal_wind_direction.upper()]
    print(f"Setting horizontal wind direction to {h_vane}")
    desired_state.horizontal_wind_direction = h_vane
    controls |= Controls.LeftRightWindDirect
if args.power_saving:
    ps = args.power_saving.upper() == "ON"
    print(f"Setting power saving to {ps}")
    desired_state.is_power_saving = ps
    controls08 |= Controls08.PowerSaving
if args.power:
    power = PowerOnOff[args.power]
    print(f"Setting power to {power}")
    desired_state.power_on_off = power
    controls |= Controls.PowerOnOff

if args.reboot:
    print("Sending reboot command...")
    ctrl.api.send_reboot_request()

if controls != Controls.NoControl:
    new_state = ctrl._send_general_control_command(desired_state, controls)

if controls08 != Controls08.NoControl:
    new_state = ctrl._send_extend08_command(desired_state, controls)

if controls != Controls.NoControl or controls08 != Controls08.NoControl:
    print(f"Updates sent, waiting {ctrl.wait_time_after_command} seconds to see changes...")
    time.sleep(ctrl.wait_time_after_command)
    ctrl.fetch_status()

print(ctrl.get_unit_info())
print("Profile codes:")
for code in ctrl.profile_code:
    print("    " + code.hex(" "))
pprint(ctrl.state.general)
pprint(ctrl.state.sensors)
pprint(ctrl.state.energy)
pprint(ctrl.state.errors)
pprint(ctrl.state._unknown5)
pprint(ctrl.state.auto_state)
