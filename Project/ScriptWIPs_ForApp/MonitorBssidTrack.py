"""
Script to capture WiFi packets from a specific access point and save them to a file.

Requires monitor mode to already be running via MonitorModeManager.py.
Uses the interface defined in config.py.

Usage:
    1. Start monitor mode:  sudo python MonitorModeManager.py
    2. Find your BSSID:     sudo python MonitorBssidSwitch.py
    3. Track the target:    sudo python MonitorBssidTrack.py <channel> <BSSID>

Example:
    sudo python MonitorBssidTrack.py 11 00:11:22:33:44:55
    sudo python MonitorBssidTrack.py 11 00:11:22:33:44:55 --output /home/kali/Desktop/capture

airodump-ng flags used:
    -c <channel>                Lock adapter to a specific Wi-Fi channel
    --bssid XX:XX:XX:XX:XX:XX   Filter capture to one access point
    -w <path>                   File path/prefix for saved capture files (.cap, .csv, etc.)
"""

import argparse
import os
import sys
import subprocess

from config import MON_INTERFACE, MM_LOCK_FILE, OUTPUT_DIR


def check_monitor_mode():
    """Verify that monitor mode is active by checking for the lock file."""
    if not os.path.exists(MM_LOCK_FILE):
        print("[!] Monitor mode is not active.")
        print("    Start it first:  sudo python MonitorModeManager.py")
        sys.exit(1)
    print(f"[+] Monitor mode confirmed active on {MON_INTERFACE}")


def main():
    parser = argparse.ArgumentParser(
        description="Capture packets from a specific BSSID while monitor mode is active."
    )

    parser.add_argument("channel",
        help="The Wi-Fi channel of the target network (e.g., 1, 6, 11)")

    parser.add_argument("BSSID",
        help="The target network's BSSID/MAC address (e.g., AA:BB:CC:DD:EE:FF)")

    parser.add_argument("--output", "-o",
        default=OUTPUT_DIR,
        help=f"Output directory/prefix for capture files (default: {OUTPUT_DIR})")

    args = parser.parse_args()

    check_monitor_mode()

    print(f"[*] Tracking BSSID: {args.BSSID}")
    print(f"    Channel:   {args.channel}")
    print(f"    Interface: {MON_INTERFACE}")
    print(f"    Output:    {args.output}")
    print()

    # airodump-ng is interactive — run without suppressing output
    subprocess.run(
        f"airodump-ng -c {args.channel} --bssid {args.BSSID} -w {args.output} {MON_INTERFACE}",
        shell=True,
        check=False
    )


if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("Error: This script must be run as sudo.")
    main()

    main()