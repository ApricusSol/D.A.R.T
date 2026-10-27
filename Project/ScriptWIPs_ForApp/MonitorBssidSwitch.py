""" 
Script to capture wifi packets from different BSSIDs 

Brings monitor mode up when ran, when ended bring it down and reset network settings

NOTE - Must have constant variables set for desired MM interface and output directory
"""

import os
import sys
import atexit

#import run command function
from RunCommand import run_command

""" set constant of which network adapter to use and the output directory. Run "ifconfig" to identify which wireless adapter you want to use. For this script, I am using the ALFA AWUS036ACM on wlan1 """
INTERFACE = "wlan1"
OUTPUT_DIR = "~/Desktop"


def on_exit():
    run_command("airmon-ng stop {INTERFACE}mon")
    run_command("systemctl restart NetworkManager")

if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("Error: This script must be run as sudo.")

    atexit.register(on_exit)

    run_command(f"airmon-ng check kill") # stop processes that would interfere with the WiFi interface
    run_command(f"irmon-ng start {INTERFACE}") # start desired network adapter in monitor mode
    run_command(f"airodump-ng {INTERFACE}mon") # list WiFi networks in range, find the target's BSSID