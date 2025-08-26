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
                    type=lambda s: s.upper(), choices=["ON", "OFF"])
parser.add_argument("--mode", help="Set operating mode",
                    type=lambda s: s.upper(), choices=[_.name for _ in DriveMode])
parser.add_argument("--target-temperature", help="Set target temperature", type=float)
parser.add_argument("--fan-speed", help="Set fan speed",
                    type=lambda s: s.upper(), choices=[_.name for _ in WindSpeed])
parser.add_argument("--vertical-wind-direction", help="Set vertical vane position",
                    type=lambda s: s.upper(), choices=[_.name for _ in VerticalWindDirection])
parser.add_argument("--horizontal-wind-direction", help="Set horizontal vane position",
                    type=lambda s: s.upper(), choices=[_.name for _ in HorizontalWindDirection])
parser.add_argument("--power-saving", help="Set power saving",
                    type=lambda s: s.upper(), choices=["ON", "OFF"])
args = parser.parse_args()

logging.basicConfig(level=logging.WARNING - 10 * args.verbose)
logger = logging.getLogger(__name__)

ctrl = MitsubishiController.create(args.host)

ctrl.fetch_status()
desired_state = ctrl.state.general
update_state = False

if args.mode:
    _ = DriveMode[args.mode.upper()]
    print("Setting mode to {}".format(_))
    ctrl.set_mode(_)
    update_state = True
if args.target_temperature:
    print("Setting target temperature to {}".format(args.target_temperature))
    ctrl.set_target_temperature(args.target_temperature)
    update_state = True
if args.fan_speed:
    _ = WindSpeed[args.fan_speed.upper()]
    print("Setting fan speed to {}".format(_))
    ctrl.set_fan_speed(_)
    update_state = True
if args.vertical_wind_direction:
    _ = VerticalWindDirection[args.vertical_wind_direction.upper()]
    print("Setting vertical wind direction to {}".format(_))
    ctrl.set_vertical_vane(_)
    update_state = True
if args.horizontal_wind_direction:
    _ = HorizontalWindDirection[args.horizontal_wind_direction.upper()]
    print("Setting horizontal wind direction to {}".format(_))
    ctrl.set_horizontal_vane(_)
    update_state = True
if args.power_saving:
    _ = args.power_saving.upper() == "ON"
    print("Setting power saving to {}".format(_))
    ctrl.set_power_saving(_)
    update_state = True
if args.power:
    # Keep power for last, so we can configure the unit correctly before switching on
    _ = args.power.upper() == "ON"
    print("Setting power to {}".format(_))
    ctrl.set_power(_)
    update_state = True

if args.reboot:
    print("Sending reboot command...")
    ctrl.api.send_reboot_request()

if update_state:
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
