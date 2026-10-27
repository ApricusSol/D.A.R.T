"""
Shared configuration constants for D.A.R.T. monitor mode scripts.

All scripts that need monitor mode should import from here instead of
hardcoding interface names and paths in multiple places.

To find your wireless adapter name, run `ifconfig` or `iwconfig` in the terminal.
"""

import os

# The wireless adapter interface name
INTERFACE = "wlan1"

# The monitor mode interface name created by airmon-ng (INTERFACE + "mon")
MON_INTERFACE = f"{INTERFACE}mon"

# Lock file path — signals to other scripts that monitor mode is active
MM_LOCK_FILE = "/tmp/dart_mm.lock"

# Default output directory for packet captures
ACTUAL_USER = os.environ.get("SUDO_USER", "user")
OUTPUT_DIR = f"/home/{ACTUAL_USER}/Desktop"

