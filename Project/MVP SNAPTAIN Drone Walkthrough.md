# MVP SNAPTAIN Drone Walkthrough

**Target:** SNAPTAIN S5C Elite
**Goal:** Pull the live video feed directly off the drone, bypassing the official app entirely.
**Status:** Complete — live video streams end-to-end with no OEM app involved.

---

## 1. General Info

A lot of this information was found from a study that another group did on a RYZE TELLO Drone.

https://www.diva-portal.org/smash/record.jsf?pid=diva2%3A1586253&dswid=8978

For our setup, however, we are using the SNAPTAIN S5C Elite, which is similar, but certain port numbers and setups had to be adjusted.

For this walkthrough I'll include pictures from both the RYZE TELLO hack as well as my own.

---

## 2. Kali Setup

I used a USB with a bootable Kali instance on it. I made this using Rufus and two USBs, one to run the Kali install on the other one. This setup allows me to hot-swap between Windows and Linux on boot, so I don't have to have a dedicated laptop for this.

---

## 3. Reconnaissance

### 3.1 NMAP

Since this is a walkthrough to understand how to perform one of these attacks, we're going to cheat a little to identify the UDP and TCP ports that the drone communicates on.

To do this we will run nmap while connected to the drone's WiFi.

**Problem:** Couldn't keep the drone powered on long enough to perform the scan. Later resolved by confirming the port directly via `nc`/packet capture instead (see Section 5.3).

### 3.2 Monitor Mode

"RFMON (Radio Frequency MONitor) is one of eight modes that 802.11 wireless cards can operate in. It allows a computer with a wireless network interface to monitor all traffic received on a wireless channel without having to associate with an access point (AP) or ad hoc network first."

Monitor mode is a setting for a wireless card that allows you to view all WiFi-based traffic around you, and is essential for getting the necessary data on the drone's network.

In order to run monitor mode you will want a wireless adapter that you can plug into your laptop. I used the **ALFA AWUS036ACM**. This allows me to do more than what my normal NIC could do. The nice thing about this adapter is that the drivers come built in, so you don't have to go through dependency hell to get it set up — it just works.

```
# ifconfig                      -- find the interface of the wireless adapter (e.g. wlan0/wlan1)
# airmon-ng check kill           -- stop processes that would interfere with the WiFi interface
# airmon-ng start wlan0          -- start wlan0 in monitor mode
# airodump-ng wlan0mon           -- list WiFi networks in range, find the target's BSSID
```

Change `wlan0` to whichever adapter you're using (mine was `wlan1`). You'll probably need `sudo` for most of these.

To stop monitor mode:
```
# airmon-ng stop wlan1mon
# systemctl restart NetworkManager
```

```
# airodump-ng -c <channel> --bssid XX:XX:XX:XX:XX:XX -w /home wlan0mon
```
Shows clients connected to the target network. `-w` is the directory to save the capture file (includes the WPA handshake, if any).

### 3.3 Deauth

```
# aireplay-ng -0 10 -a XX:XX:XX:XX:XX:XX wlan0mon
```
Disconnects a client by injecting 10 deauth packets. When the client reconnects, its WPA handshake can be captured.

**Note:** Useful if we ever need to attack encryption — not needed here since the drone's AP turned out to be open (see Section 5.1).

---

## 4. Drone Hacking

### 4.1 DDOS

`hping2`: sends custom TCP, UDP, ICMP, and raw IP packets with control over nearly every header field.

```
# sudo hping2 -c 1500 -d 120 -S -w 64 -p 8866 --flood --rand-source 172.19.10.1
```
- `-c 1500` — send 1500 packets
- `-d 120` — pad each packet to 120 bytes
- `-S` — SYN flag
- `-w 64` — TCP window size
- `-p 8866` — target port (now confirmed correct — see Section 5.3)
- `--flood` — fire as fast as possible
- `--rand-source` — spoof source IP per packet

### 4.2 MITM (ARP Spoof)

```
# sysctl -w net.ipv4.ip_forward=1
```
Enables packet forwarding so the attacker machine can act as a router.

```
# arpspoof -i wlan1 -t 172.19.10.100 172.19.10.1
```
Tells the controller/phone that packets meant for the drone should go to the attacker's MAC instead.

```
# arpspoof -i wlan1 -t 172.19.10.1 172.19.10.100
```
(run in a second terminal, alongside the first) — the reverse: tells the drone that packets meant for the controller should go to the attacker instead.

Replace `.100` with the phone's actual IP (check its WiFi settings).

---

## 5. Video Stream Interception

This is where the project moved from basic recon into full protocol reverse-engineering — understanding the proprietary video and authentication protocol well enough to pull the feed with our own code, no OEM app involved.

### 5.1 Capture Methodology (Wireshark + Monitor Mode)

Two capture setups, depending on whose traffic we needed to see:

**Setup A — capturing our own machine's traffic.** When our Kali box was itself one of the endpoints (e.g. testing our own Python script against the drone), a normal association + standard interface capture was enough:
```bash
sudo tcpdump -i wlan0 -w capture.pcap
```
No monitor mode needed — traffic to/from your own machine is visible to a normal capture.

**Setup B — capturing the official app's traffic as a third party.** To see the handshake between the *phone app* and the drone, our laptop had to passively observe traffic between two other devices. Requires the Alfa adapter in monitor mode:
```bash
sudo airmon-ng check kill
sudo airmon-ng start wlan1
iwconfig                                  # confirm the monitor interface name (e.g. wlan1mon)
sudo iwconfig wlan1mon channel <channel>  # match the drone's channel
sudo tcpdump -i wlan1mon -w capture.pcap
```

The drone's AP is **open (no WPA2)**, so no decryption keys were needed in Wireshark — IP/TCP headers were visible directly.

**Known limitation:** monitor-mode captures showed regular packet loss (`[TCP ACKed unseen segment]`, `[TCP Previous segment not captured]`, retransmission markers). This is normal for passive monitor-mode capture and didn't block analysis, but it's the likely cause of the occasional single-frame visual glitch seen during live playback later (Section 7.3) — worth remembering if frame data ever looks corrupted or incomplete.

### 5.2 Useful Display/Capture Filters

```
ip.addr == 172.19.10.1                        # drone traffic only
ip.addr == 172.19.10.1 && tcp.port == 8866     # the video/control socket
tcp.stream eq 0                                # isolate one TCP conversation
frame.number <= 200                            # cap display before exporting a trimmed pcap
```
Capture filter (keeps the saved file small):
```
host 172.19.10.1 and tcp
```

**Finding the right stream among several open sockets:** `Statistics → Conversations → TCP` in Wireshark lists every TCP stream with byte counts — the video stream stands out immediately by throughput. (This observation turned out to matter a lot more than expected — see Section 6.)

**Extracting clean TCP payload:** right-click a packet → **Follow → TCP Stream** → "Show data as" **Hex Dump**. Copying raw "frame bytes" from the packet list includes the 802.11 MAC header + LLC/SNAP encapsulation on top of the real payload (24 bytes 802.11 header + 2 bytes QoS + 8 bytes LLC/SNAP + 20 bytes IP header + variable TCP header, no 802.11 encryption here). Sanity-check this offset math against a known packet (e.g. a plain ACK) before trusting extraction on data-carrying packets.

### 5.3 Initial Port/Protocol ID

Confirmed via `nc` and nmap-style probing:
- **IP:** `172.19.10.1` (drone — confirmed from captures and the `devicesIP` field in decompiled Java)
- **Port:** `8866` (TCP) — ports 8888 and 7070 both returned connection refused
- **Transport:** raw TCP, not RTSP — no RTSP handshake, no standard media framing

```bash
nc 172.19.10.1 8866 | xxd
```
Connects successfully but returns zero bytes — the socket accepts a connection but won't send anything until a valid application-layer handshake completes. First sign that this protocol has its own auth layer on top of an otherwise-open WiFi network.

### 5.4 Video Frame Format

By capturing genuine app traffic (monitor mode) and extracting raw TCP payload bytes, the video stream, once flowing, turned out to be **raw H.264 Annex-B elementary stream, wrapped in a custom 44-byte header per frame**:

```
Offset  Bytes                     Meaning
0-3     00 00 01 a0 (or a1)       Sync marker. a1 = keyframe/SPS+PPS carrier, a0 = regular P-frame
4-9     00 01 00 00 00 00         Fixed
10-11   varies                    Frame sequence counter (big-endian u16)
12-15   00 08 00 00               Fixed
16-17   varies                    Secondary counter/sub-field
18-23   00 00 00 00 00 00         Fixed
24-31   d0 02 00 05 00 00 00 00   Fixed (codec/stream type marker)
32-35   varies                    Timestamp, little-endian u32
36-43   00000000 00000000 3a      Fixed, ends in 0x3a
44-46   00 00 01                  Real H.264 Annex-B start code
47+     ...                       NAL unit data
```

Derived by diffing consecutive captured video packets byte-by-byte, cross-validated against the full 802.11+LLC+IP+TCP offset math to confirm we were reading real payload and not MAC-layer artifacts.

**Confirmed correct end-to-end** by building an automated extractor (`extract_h264.py`, Section 7.1) that strips this header from a live capture and feeds the result into `ffplay` — producing clean, standard H.264 video.

### 5.5 The Authentication Handshake

#### 5.5.1 Decompiling the App

The Snaptain FPV APK (`SNAPTAIN+FPV_1.8.8_APKPure`) was decompiled with **jadx-gui**. Key finding: the app is built almost entirely on a white-labeled OEM drone SDK (`com.netopsun.fhdevices`, native library `FHExtraJni`), not bespoke Snaptain code. A Chinese OEM (likely "guanxukeji", per decoded credential strings) supplies the camera module + protocol stack, and the brand (Snaptain) just skins the app around it. This is a known pattern in budget drone hardware.

Relevant class: `FHDevices.java`. Found hardcoded, Base64-encoded credentials:

| Field | Base64 | Decoded |
|---|---|---|
| userName | `Z3Vhbnh1a2VqaQ==` | `guanxukeji` |
| password | `Z3hyZHc2MA==` | `gxrdw60` |
| aesKey | `Z3Vhbnh1a2pAZmg4NjIwLg==` | `guanxukj@fh8620.` |
| userName2 | `Z3Vhbnh1a2VqaTI=` | `guanxukeji2` |
| password2 | `Z3hyZHc2MDI=` | `gxrdw602` |

The login/session logic (`IFNeedInitDevices()`) packages these into byte buffers and hands them to native JNI calls (`FHDEV_NET_Login`, `FHDEV_NET_SetCryptKey`) in `libFHExtraJni.so`.

#### 5.5.2 Confirming via Public Research

A public Synacktiv writeup ("From cheap IoT toy to your smartphone: Getting RCE by leveraging a companion app", July 2025) analyzed the *same* underlying OEM library family (`libFHDEV_Net.so` / `FHDEV_NET_Login` / `FHDEV_NET_SetCryptKey`) on a different rebrand (Eachine E58 / "lewei"). This confirmed:
- A fixed packet envelope with a magic header, followed by AES-encrypted payload
- Login packets contain username/password pairs encrypted with a static, hardcoded AES key
- An `NC()` send/receive wrapper handles all authenticated traffic, keyed by `cmd_id`/`seq_id`
- Each OEM customer ships its own hardcoded credentials/key, but the protocol *structure* is identical across rebrands

Major confirmation that we were on the right track without needing to disassemble the `.so` ourselves.

#### 5.5.3 Reverse-Engineering the Login Packet

Captured a real login exchange (monitor mode) and extracted the raw 106-byte TCP payload sent by the phone on connecting:
```
49 54 64 00 00 00 52 00 00 00 [96 bytes of AES-128-ECB ciphertext]
```
Breaking this down:
- `49 54 64 00` = ASCII `"ITd"` + null byte
- (later revised — see Section 6.2: byte 2 is actually a per-connection-purpose command byte, not part of a fixed 4-byte magic)
- `00 00` = command/type field
- `52 00 00 00` = length field, little-endian u32
- Remaining 96 bytes = 6 AES blocks of ciphertext

**Decryption confirmed the key works:** using AES-128-ECB with key `guanxukj@fh8620.`, decrypted the ciphertext and recovered recognizable plaintext fragments: `"keji"`, `"guanxu"`, `"gxrdw6"`, `"0"` — i.e. `guanxukeji` / `gxrdw60`, split across block boundaries with zero-padding. A second captured session (secondary login identity) decrypted to `"keji2"` / `"02"`, confirming the fallback credential path and giving two independent data points to validate the layout.

**This let us build our own login packet from scratch** (`build_login_packet()`), reconstructing the plaintext layout and re-encrypting with the known key.

#### 5.5.4 Testing Against the Real Drone

Sending our constructed login packet directly to port 8866 (no phone app involved) produced a **genuine 106-byte response from the drone**, decrypting cleanly with the same key and containing what appeared to be a session confirmation including `172.19.10.103` — strong evidence the handshake was accepted.

---

## 6. Resolving the "Start Play" Mystery

### 6.1 The Original Blocker

Despite a successful login, connecting and waiting still yielded **zero video frames**. The decompiled Java showed why: `FHVideoCommunicator.connectInternal()` calls a *second*, distinct native function — `startRealPlay(userID, previewStructPointer, directBuffer, callback)` — only after login succeeds, passing an `LPFHNP_Preview_t_struct` (transport mode, blocking flag, encoder ID). This call was handled **entirely inside the native `.so`** — no Java-visible packet construction for this step, unlike login.

At this point the leading hypothesis was that "start play" was a distinct command (another `NC()`-style request, per the Synacktiv model) built inside compiled ARM code we hadn't inspected — meaning the next step might require disassembling `libFHExtraJni.so` in Ghidra to see exactly what bytes it sends.

### 6.2 Testing Before Disassembling

Rather than committing to Ghidra up front, we built tooling to capture a real login-to-video session and automatically map every packet on the wire between login and the first video frame, decrypting each one — the idea being: if the structure is simple, we might never need to disassemble anything.

**First attempt** found a second 106-byte login-shaped packet immediately after the first — but decrypting it revealed the *same* username/password as the original login. This was a different discovery than expected: not a "start play" command, but confirmation that the drone's control channel re-sends login-shaped packets (likely heartbeat-related), and other short-lived device-metadata exchanges (device config / `GetDevConfig`, periodic device-name broadcast) were also happening on that same socket — all before any video appeared at all.

**Critical realization:** `Statistics → Conversations → TCP` showed the capture actually contained **six separate TCP streams** to port 8866, not one. The original mapping had only been looking at the first stream (the one carrying the initial login), which never carried video at all.

### 6.3 The Actual Answer

Re-running the stream-mapping tooling across *all* streams found exactly one that carried video frames. Mapping that stream specifically showed:

- One single login-type packet (`0x64`)
- Followed ~0.08–0.10 seconds later, directly, by video frame data (`00 00 01 a1`)
- **No other command type ever appears on this connection, across two independent full-length captures, byte-for-byte identical both times.**

**Conclusion: there is no separate "start play" command at all.** The app opens a **second, dedicated TCP connection** purely for video, and simply logging in on that second connection is what triggers streaming. The drone's "response to login" on this socket *is* the first video frame — not a protocol ack.

This fully resolved the question that had pointed toward Ghidra, without needing to disassemble the native library.

### 6.4 Recovered Video-Channel Login Packet

Diffing the video-channel login's decrypted plaintext against the original control-channel login (both 96-byte AES-128-ECB blocks, same key) revealed two differences:

```
control login (type=07): ...0x4f: 01   0x50: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
video login   (type=04): ...0x4f: 0c   0x50: 00 00 02 01 00 00 00 00 0e 00 00 00 00 00 00 00
```

1. **Offset 0x03** (connection-purpose byte): `0x07` on the control channel, `0x04` on the video channel.
2. **Offset 0x4f onward**: control login is all zero-padding; video login has `0x0c` (length=12) followed by a 12-byte struct: `00 00 02 01 00 00 00 00 0e 00 00 00`.
   - Byte `0x52 = 02` lines up with `btEncID = 2` (the app's default quality setting)
   - Byte `0x53 = 01` lines up with the hardcoded `btBlocked = 1`
   - Trailing `0x0e` (14) — meaning unconfirmed

This is the exact wire encoding of the `LPFHNP_Preview_t_struct` visible in the decompiled Java, recovered purely by observation and diffing — no disassembly needed. Full layout documented in `open_video_channel.py`.

**Open item:** only one quality setting (`btEncID=2`) has been captured/confirmed so far. Capturing a session with the app's quality setting switched (if exposed in its UI) and diffing against this layout would confirm which byte(s) control quality/encoder, rather than relying on the Java-code inference alone.

---

## 7. End-to-End Extraction & Live Streaming

With the full protocol understood, this was turned into an actual working video feed, no OEM app involved at any point. (Built initially as three separate scripts while working through each piece; consolidated afterward into one tool — `s5c_video.py`, Section 8 — once all three were individually verified.)

### 7.1 Header Stripping (`extract_h264.py`)

Strips the 44-byte wrapper header documented in Section 5.4 from a raw captured byte stream and reassembles a plain H.264 Annex-B file.

**Important detail:** matching frame boundaries on just the 3-byte `00 00 01` sync prefix is **not safe** — a single wrapped frame's payload can itself contain multiple H.264 NAL units (SPS, PPS, slice), each with its own native Annex-B start code that also begins `00 00 01`. The extractor instead matches the *full* combination of fixed fields from the documented header (offsets 4–9, 12–15, 18–23, 24–31, and the trailing `0x3a` at offset 43), which is specific enough not to collide with compressed video data.

Includes a `--debug-nals` flag that parses and prints the NAL type (SPS/PPS/P-slice/etc.) and size for the first N frames — used to diagnose a real bug (next item) rather than guess at it.

**Bug found and fixed:** early captures showed clean motion but garbled decode for the first several seconds (`ffplay` reporting `non-existing PPS 0 referenced`). Using `--debug-nals`, traced this to the capture script (`open_video_channel.py`) discarding the drone's very first reply — which, per Section 6.3, *is* the first video frame — instead of writing it to the output file. Fixed by writing that first response into the capture before entering the main read loop. After the fix, playback was clean from frame 1 with no decoder errors on one full run, and only a single, self-correcting macroblock error on another (expected — see Section 7.3).

### 7.2 One-Shot Capture (`open_video_channel.py`)

Opens a fresh TCP connection, sends the reconstructed video-channel login packet (Section 6.4), and dumps everything received for N seconds to a file. Flags the moment it sees video-frame sync bytes in the stream, and supports `--bt-enc-id 1` to try the alternate quality value if needed.

### 7.3 Live Streaming (`live_stream.py`)

Combines the connection/login logic from 7.2 with the header-stripping logic from 7.1, run continuously: reads from the socket in a loop, incrementally detects complete frames in the buffer (correctly handling frames split across arbitrary TCP chunk boundaries — verified against synthetic multi-chunk test data before use), strips each frame's header, and pipes the raw H.264 directly into `ffplay`'s stdin in real time. Supports `--tee <file>` to also save a raw copy while watching live.

**Result: confirmed working live view**, connecting directly to the drone with no OEM app involved.

**Known cosmetic issue:** occasional single-frame visual glitch ("layered"/smeared look) during playback, self-correcting within a frame or two. Consistent with the packet-loss behavior already noted in Section 5.1 (monitor-mode capture, and now live TCP reception over open WiFI with no retransmission/error-resilience layer at the application level) — not a bug in the extraction logic, confirmed by it affecting only isolated frames rather than corrupting the stream going forward.

---

## 8. Tools/Artifacts Produced

**Current tool:**

- **`s5c_video.py`** — the consolidated, maintained tool. One script, three subcommands, sharing a single tested implementation of login-packet construction and frame-boundary detection instead of three separate copies of the same logic:
  - `live` — connects, authenticates on the dedicated video channel, and pipes the live feed straight into `ffplay` in real time (optionally also saving a raw copy with `--tee`). This is the normal way to just watch the feed.
  - `capture` — same connection/login, but dumps the raw stream to a file for a fixed duration instead of displaying it.
  - `extract` — post-processes a raw file from `capture` (or `live --tee`) into a plain, playable `.h264` file, with `--debug-nals` and `--start-at-keyframe` diagnostic/recovery flags for when something looks wrong.

  ```bash
  python3 s5c_video.py live --host 172.19.10.1 --port 8866
  python3 s5c_video.py capture --host 172.19.10.1 --port 8866 --out raw.bin --duration 10
  python3 s5c_video.py extract --in raw.bin --out out.h264 --debug-nals 5
  ```

**Superseded (kept for reference/history only):**

- `s5c_video_extractor.py` — original script: TCP connect, AES-128-ECB login packet construction/sending, initial H.264 frame extraction logic, from before the video-channel/login mechanism was understood.
- `find_startplay_packet.py` — captures-to-table research tool: maps every TCP stream in a pcap, identifies which one(s) carry login vs. video traffic, parses and auto-decrypts envelope packets by command type, and diffs login plaintexts against each other. This is what actually found the video-channel mechanism (Section 6) — not superseded in purpose, just a one-off research tool rather than something you'd run day-to-day, so it isn't folded into `s5c_video.py`.
- `open_video_channel.py`, `extract_h264.py`, `live_stream.py` — the three intermediate scripts, each individually built and verified while figuring this out, now merged into `s5c_video.py` above. Their logic was ported over and re-validated (not rewritten from scratch) before being retired.

---

## 9. Remaining Open Items

Everything required to view the live feed is done. A few loose ends remain if this is extended further:

1. **Quality/encoder byte confirmation.** Only `btEncID=2` has been captured. Diff a session captured with a different in-app quality setting against the recovered layout (Section 6.4) to confirm which byte(s) actually control it, and what the trailing `0x0e` field means.
2. **UDP transport path.** The Java (`FHDevices.setParams`) checks for a `"udp"` transport mode (`rxtxTransMode`) that was never exercised here — everything so far has used the TCP path. Unexplored, not needed for current goal.
3. **Heartbeat behavior on the video channel.** The control channel showed periodic heartbeat-shaped traffic; unclear whether the video channel needs anything similar for long-running sessions beyond the test durations used here (up to ~15s tested cleanly).
4. ~~**Merge into one tool.**~~ Done — see `s5c_video.py` (Section 8).
