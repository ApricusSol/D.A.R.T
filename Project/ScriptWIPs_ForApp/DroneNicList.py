"""
Drone NIC/OUI Prefix Extractor for D.A.R.T.

Parses the Wireshark manuf (OUI) database and extracts MAC address
prefixes belonging to known commercial drone manufacturers. The
resulting lookup table can be used by monitoring scripts to flag
drone-related traffic in captured 802.11 frames.

Requires manuf.txt to already exist — run DownloadOuiList.py first
(before entering monitor mode, since the download needs network access).

Usage:
    As a standalone tool (prints matches):
        python DroneNicList.py
        python DroneNicList.py --manuf /path/to/manuf.txt

    As an importable module:
        from DroneNicList import load_drone_ouis
        drone_ouis = load_drone_ouis()          # dict: OUI prefix -> manufacturer name
        prefixes   = set(drone_ouis.keys())      # set of prefix strings for fast lookup
"""

import argparse
import os
import sys

# ---------------------------------------------------------------------------
# Drone manufacturer keywords
# ---------------------------------------------------------------------------
# These are matched (case-insensitive) against the full manufacturer name
# in the manuf file. Add new vendors here as needed.
DRONE_KEYWORDS = [
    "dji", "parrot", "skydio", "yuneec", "autel",
    "holy stone", "hubsan", "ryze",
    "aerovironment", "shenzhen aee",
    # OEM chipset/module vendors commonly found inside consumer drones
    "espressif",           # ESP8266/ESP32 modules used in many budget drones
    "guanxu",              # OEM behind Snaptain and similar rebrands
    "snaptain",
]

# Default path: same directory as this script
DEFAULT_MANUF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manuf.txt")


def load_drone_ouis(manuf_path=DEFAULT_MANUF_FILE):
    """Parse the Wireshark manuf file and return drone-related OUI entries.

    The manuf file is tab-separated with three columns:
        <MAC prefix>    <Short name>    <Full manufacturer name>

    Lines starting with '#' are comments. Some entries only have two
    columns (no long name), in which case the short name is used instead.

    Args:
        manuf_path: Path to the Wireshark manuf.txt file.

    Returns:
        A dict mapping OUI prefix strings (e.g. "AA:BB:CC") to the
        manufacturer name. Returns an empty dict if the file is missing.
    """
    drone_ouis = {}

    if not os.path.isfile(manuf_path):
        print(f"[!] manuf file not found: {manuf_path}")
        print("    Run DownloadOuiList.py first (before entering monitor mode).")
        return drone_ouis

    with open(manuf_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Skip comments and blank lines
            if not line or line.startswith("#"):
                continue

            # Split on tab(s); filter out empty fields from double-tabs
            parts = [p for p in line.split("\t") if p.strip()]

            if len(parts) < 2:
                continue

            oui_prefix = parts[0].strip()
            # Prefer the long name (column 3) if present, else the short name
            manufacturer = parts[-1].strip() if len(parts) >= 3 else parts[1].strip()

            # Check if any drone keyword appears in the manufacturer name
            name_lower = manufacturer.lower()
            if any(keyword in name_lower for keyword in DRONE_KEYWORDS):
                drone_ouis[oui_prefix] = manufacturer

    return drone_ouis


def main():
    parser = argparse.ArgumentParser(
        description="Extract drone-related OUI prefixes from the Wireshark manuf database."
    )
    parser.add_argument(
        "--manuf", "-m",
        default=DEFAULT_MANUF_FILE,
        help=f"Path to manuf.txt (default: {DEFAULT_MANUF_FILE})"
    )
    args = parser.parse_args()

    drone_ouis = load_drone_ouis(args.manuf)

    if not drone_ouis:
        print("[!] No drone-related OUIs found.")
        print("    Check that manuf.txt exists and is not empty.")
        sys.exit(1)

    print(f"[+] Found {len(drone_ouis)} drone-related OUI prefix(es):\n")
    for oui, manufacturer in sorted(drone_ouis.items()):
        print(f"    {oui:<24s} {manufacturer}")

    print(f"\n[+] These prefixes can be used to filter 802.11 frames for drone traffic.")


if __name__ == "__main__":
    main()
