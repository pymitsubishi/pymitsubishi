import argparse
import logging
import time
from pprint import pprint

from . import WindSpeed
from .mitsubishi_controller import MitsubishiController
from .mitsubishi_parser import PowerOnOff, DriveMode, WindSpeed, VerticalWindDirection, HorizontalWindDirection

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--verbose", "-v", help="More verbose output (up to 2 times)", action="count", default=0)
parser.add_argument("host", help="Hostname or IP address to connect to, optionally followed by ':port'")
parser.add_argument("--reboot", help="Request the device to reboot", action="store_true")
parser.add_argument("--power", help="Set power",
                    type=lambda s: s.upper(), choices=[_.name for _ in PowerOnOff])
parser.add_argument("--mode", help="Set operating mode",
                    type=lambda s: s.upper(), choices=[_.name for _ in DriveMode])
parser.add_argument("--target-temperature", help="Set target temperature", type=float)
parser.add_argument("--wind-speed", help="Set wind speed",
                    type=lambda s: s.upper(), choices=[_.name for _ in WindSpeed])
parser.add_argument("--vertical-wind-direction", help="Set vertical vane position",
                    type=lambda s: s.upper(), choices=[_.name for _ in VerticalWindDirection])
parser.add_argument("--horizontal-wind-direction", help="Set horizontal vane position",
                    type=lambda s: s.upper(), choices=[_.name for _ in HorizontalWindDirection])
args = parser.parse_args()

logging.basicConfig(level=logging.WARNING - 10 * args.verbose)
logger = logging.getLogger(__name__)

ctrl = MitsubishiController.create(args.host)

ctrl.fetch_status()
desired_state = ctrl.state.general
update_state = {}

if args.power:
    desired_state.power_on_off = PowerOnOff[args.power.upper()]
    update_state["power_on_off"] = True
if args.mode:
    desired_state.drive_mode = DriveMode[args.mode.upper()]
    update_state["drive_mode"] = True
if args.target_temperature:
    desired_state.temperature = args.target_temperature
    update_state["temperature"] = True
if args.wind_speed:
    desired_state.wind_speed = WindSpeed[args.wind_speed.upper()]
    update_state["wind_speed"] = True
if args.vertical_wind_direction:
    desired_state.vertical_wind_direction = VerticalWindDirection[args.vertical_wind_direction.upper()]
    update_state["up_down_wind_direct"] = True
if args.horizontal_wind_direction:
    desired_state.horizontal_wind_direction = HorizontalWindDirection[args.horizontal_wind_direction.upper()]
    update_state["left_right_wind_direct"] = True

if update_state:
    print("Updating state...")
    ctrl._send_general_control_command(desired_state, update_state)
    print("Waiting 3 seconds to see changes...")
    time.sleep(3)
    ctrl.fetch_status()

if args.reboot:
    print("Sending reboot command...")
    ctrl.api.send_reboot_request()

print("Profile codes:")
for code in ctrl.profile_code:
    print("    " + code.hex(" "))
pprint(ctrl.state.general)
pprint(ctrl.state.sensors)
pprint(ctrl.state.energy)
pprint(ctrl.state.errors)
pprint(ctrl.state._unknown5)
pprint(ctrl.state._unknown9)
#pprint(ctrl.get_status_summary())
