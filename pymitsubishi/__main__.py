import argparse
import logging
from pprint import pprint
import time

from .mitsubishi_controller import MitsubishiController
from .mitsubishi_parser import (
    DriveMode,
    HorizontalWindDirection,
    PowerOnOff,
    VerticalWindDirection,
    WindSpeed,
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


def float_or_internal(arg: str) -> str | float:
    if arg.upper() == "INTERNAL":
        return "INTERNAL"
    try:
        return float(arg)
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"Argument `{arg}` is not a valid value") from err


parser.add_argument(
    "--current-temperature",
    help='Set current temperature to either "INTERNAL", or a specific value in ºC. '
    "WARNING: Setting an external temperature will effectively disable the thermostat control of the unit! "
    "This is a Write-Only setting: there is no way to see the current setting. "
    "This setting persists until a full power cycle of the heat pump.",
    metavar="TEMP_OR_INTERNAL",
    type=float_or_internal,
)

args = parser.parse_args()

logging.basicConfig(level=logging.WARNING - 10 * args.verbose)
logger = logging.getLogger(__name__)

ctrl = MitsubishiController.create(args.host)

ctrl.fetch_status()
changeset = ctrl.changeset()

if args.mode:
    drive_mode = DriveMode[args.mode.upper()]
    print(f"Setting mode to {drive_mode}")
    changeset.set_mode(drive_mode)
if args.target_temperature:
    print(f"Setting target temperature to {args.target_temperature}")
    changeset.set_target_temperature(args.target_temperature)
if args.fan_speed:
    fan_speed = WindSpeed[args.fan_speed.upper()]
    print(f"Setting fan speed to {fan_speed}")
    changeset.set_fan_speed(fan_speed)
if args.vertical_wind_direction:
    v_vane = VerticalWindDirection[args.vertical_wind_direction.upper()]
    print(f"Setting vertical wind direction to {v_vane}")
    changeset.set_vertical_wind_direction(v_vane)
if args.horizontal_wind_direction:
    h_vane = HorizontalWindDirection[args.horizontal_wind_direction.upper()]
    print(f"Setting horizontal wind direction to {h_vane}")
    changeset.set_horizontal_wind_direction(h_vane)
if args.power_saving:
    ps = args.power_saving.upper() == "ON"
    print(f"Setting power saving to {ps}")
    changeset.set_power_saving(ps)
if args.power:
    power = PowerOnOff[args.power]
    print(f"Setting power to {power}")
    changeset.set_power(power)

if args.reboot:
    print("Sending reboot command...")
    ctrl.api.send_reboot_request()

wait_for_changes = False

if not changeset.empty:
    ctrl.apply_changeset(changeset)
    wait_for_changes = True

if args.current_temperature is not None:
    t = None if args.current_temperature == "INTERNAL" else args.current_temperature
    ctrl.set_current_temperature(t)
    wait_for_changes = True

if wait_for_changes:
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
