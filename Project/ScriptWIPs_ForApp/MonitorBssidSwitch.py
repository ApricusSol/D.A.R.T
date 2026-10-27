"""
Script to scan for nearby WiFi networks and display their BSSIDs.

Requires monitor mode to already be running via MonitorModeManager.py.
Uses the interface defined in config.py.

Usage:
    1. Start monitor mode:  sudo python MonitorModeManager.py
    2. Run this script:     sudo python MonitorBssidSwitch.py
"""

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


if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("Error: This script must be run as sudo.")

    check_monitor_mode()

    print(f"[*] Scanning for networks on {MON_INTERFACE}...")
    print("    Press Ctrl+C when you've found your target BSSID.\n")

    # airodump-ng is interactive (ncurses) — run without suppressing output
    subprocess.run(f"airodump-ng {MON_INTERFACE}", shell=True, check=False)