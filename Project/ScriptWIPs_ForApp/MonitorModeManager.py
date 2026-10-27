"""
Monitor Mode Manager for D.A.R.T.

Starts monitor mode on the configured wireless interface and keeps it running
until the user stops the script (Ctrl+C). While running, a lock file signals
to other D.A.R.T. scripts (MonitorBssidSwitch, MonitorBssidTrack) that monitor
mode is active and which interface to use.

Usage:
    sudo python MonitorModeManager.py

The interface is configured in config.py.
"""

import os
import sys
import signal
import atexit

from RunCommand import run_command
from config import INTERFACE, MON_INTERFACE, MM_LOCK_FILE


def create_lock_file():
    """Create the lock file to signal that monitor mode is active."""
    with open(MM_LOCK_FILE, "w") as f:
        f.write(f"pid={os.getpid()}\n")
        f.write(f"interface={INTERFACE}\n")
        f.write(f"mon_interface={MON_INTERFACE}\n")
    print(f"[+] Lock file created: {MM_LOCK_FILE}")


def remove_lock_file():
    """Remove the lock file to signal that monitor mode is no longer active."""
    if os.path.exists(MM_LOCK_FILE):
        os.remove(MM_LOCK_FILE)
        print(f"[-] Lock file removed: {MM_LOCK_FILE}")


def enable_monitor_mode():
    """Kill interfering processes and start monitor mode via airmon-ng."""
    print(f"[*] Starting monitor mode on {INTERFACE}...")
    run_command("airmon-ng check kill")
    run_command(f"airmon-ng start {INTERFACE}")
    create_lock_file()
    print(f"[+] Monitor mode active on {MON_INTERFACE}")


def disable_monitor_mode():
    """Stop monitor mode and restore network services."""
    print(f"[*] Stopping monitor mode on {MON_INTERFACE}...")
    run_command(f"airmon-ng stop {MON_INTERFACE}")
    run_command("systemctl restart NetworkManager")
    remove_lock_file()
    print("[+] Monitor mode disabled. Network services restored.")


def on_exit():
    """Cleanup handler — ensures monitor mode is always stopped on exit."""
    disable_monitor_mode()


def main():
    if os.geteuid() != 0:
        sys.exit("Error: This script must be run as sudo.")

    # Guard against running twice
    if os.path.exists(MM_LOCK_FILE):
        print(f"[!] Lock file already exists at {MM_LOCK_FILE}")
        print("    Monitor mode may already be running.")
        print("    If not, delete the lock file and try again:")
        print(f"    sudo rm {MM_LOCK_FILE}")
        sys.exit(1)

    atexit.register(on_exit)

    enable_monitor_mode()

    print()
    print("=" * 50)
    print("  Monitor Mode is ACTIVE")
    print(f"  Interface: {MON_INTERFACE}")
    print("  Press Ctrl+C to stop and restore network.")
    print("=" * 50)
    print()

    # Block until user interrupts
    try:
        signal.pause()
    except KeyboardInterrupt:
        print("\n[*] Ctrl+C received. Shutting down...")


if __name__ == "__main__":
    main()

