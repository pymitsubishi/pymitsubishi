import argparse
import logging
from pprint import pprint

from pymitsubishi import MitsubishiController

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--verbose", "-v", help="More verbose output (up to 2 times)", action="count", default=0)
parser.add_argument("host", help="Hostname or IP address to connect to, optionally followed by ':port'")
parser.add_argument("--reboot", help="Request the device to reboot", action="store_true")
args = parser.parse_args()

logging.basicConfig(level=logging.WARNING - 10 * args.verbose)
logger = logging.getLogger(__name__)

ctrl = MitsubishiController.create(args.host)

if args.reboot:
    ctrl.api.send_reboot_request()

ctrl.fetch_status()
pprint(ctrl.state.general)
pprint(ctrl.state.sensors)
pprint(ctrl.state.energy)
pprint(ctrl.state.errors)
pprint(ctrl.state._unknown5)
pprint(ctrl.state._unknown9)
pprint(ctrl.get_status_summary())
