""" 
Script to capture wifi packets from a specific AP and save them to a file. 

Note - Monitor mode must already be enabled and you must already have a BSSID you want to track from Monitor Mode BSSID Switch
"""

import argparse
import os
import sys
import atexit

#import run command function
from RunCommand import run_command

"""
airodump-ng: The packet sniffing tool.

-c <channel>: Locks the wireless adapter to listen on a specific Wi-Fi channel.

--bssid XX:XX:XX:XX:XX:XX: Filters the capture to only include traffic associated with this specific MAC address.

-w {OUTPUT_DIR}: Sets the file path and prefix where the capture files (.cap, .csv, etc.) will be saved.

{INTERFACE}mon: The wireless network interface being used to capture the traffic.


ARGS NEEDED -

<channel>: The specific Wi-Fi channel number of the target network (e.g., 1, 6, 11).

XX:XX:XX:XX:XX:XX: The MAC address (BSSID) of the target router or access point.

{OUTPUT_DIR}: The directory path and base filename for the saved files (e.g., /home/user/Desktop/capture).

{INTERFACE}mon: The name of their wireless adapter that has been put into monitor mode (e.g., wlan0mon or wlan1mon).

"""

def on_exit():
    run_command("airmon-ng stop {INTERFACE}mon")
    run_command("systemctl restart NetworkManager")

def main():
    # Make argument parser with description
    parser = argparse.ArgumentParser(description="Taking in required information to run the BSSID tracking command")

    # Add a positional argument for number of de-auth packets
    parser.add_argument("channel", help="The Wi-Fi channel number of the target network. Ex - 1, 6, 11")

    # Add a positional argument for the networks BSSID
    parser.add_argument("BSSID", help="The target networks BSSID/MAC address. Ex- XX:XX:XX:XX:XX:XX")

    # Add a positional argument (for MM network being used)
    parser.add_argument("network", help="The Network currently running monitor mode. Ex-wlan0mon")

    # Add a positional argument for the output dir for logging
    parser.add_argument("outputDir", help="The directory path and base filename for the saved files. Ex - /home/user/Desktop/capture")


    # Parse the arguments
    args = parser.parse_args()

    print(f"BSSID: {args.BSSID}")
    print(f"Channel: {args.channel}")
    print(f"Network: {args.network}")
    print(f"Output Directory: {args.outputDir}")
       
    # "airodump-ng -c <channel> --bssid XX:XX:XX:XX:XX:XX -w {OUTPUT_DIR} {INTERFACE}mon")
    # build the command
    run_command(f"airodump-ng -c {args.channel} --bssid {args.BSSID} -w {args.outputDir} {args.network}")

    """ 
    Example command format for running: 
    python MonitorBssidTrack.py 11 00:11:22:33:44:55 wlan0mon /home/kali/Desktop/capture
    """

   
if __name__ == "__main__":
    if os.geteuid() != 0:
        sys.exit("Error: This script must be run as sudo.")
    main()