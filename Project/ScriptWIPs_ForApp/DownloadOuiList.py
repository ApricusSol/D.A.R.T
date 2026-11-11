"""
Download the Wireshark OUI manufacturer database for D.A.R.T.

Downloads the latest manuf file from Wireshark's automated data
repository. This must be run BEFORE switching into monitor mode,
because airmon-ng kills the network connection.

The downloaded file is used by DroneNicList.py to build a lookup table
of drone-related MAC prefixes.

Usage:
    python DownloadOuiList.py
    python DownloadOuiList.py --output /path/to/manuf.txt
"""

import argparse
import os
import sys
import urllib.request
import urllib.error

# Default download URL and local filename
OUI_URL = "https://www.wireshark.org/download/automated/data/manuf"
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manuf.txt")


def download_oui_list(url=OUI_URL, file_path=DEFAULT_FILE):
    """Download the Wireshark OUI/manuf database to a local file.

    Args:
        url:       Remote URL to fetch the manuf file from.
        file_path: Local path to save the downloaded file.

    Returns:
        The absolute path of the saved file on success, or None on failure.
    """
    print(f"[*] Downloading OUI list from:\n    {url}")
    print(f"    Saving to: {file_path}")

    try:
        urllib.request.urlretrieve(url, file_path)
    except urllib.error.URLError as e:
        print(f"[!] Download failed (network error): {e.reason}")
        print("    Make sure you have internet access.")
        print("    This must be run BEFORE entering monitor mode.")
        return None
    except OSError as e:
        print(f"[!] Could not write file: {e}")
        return None

    # Sanity-check: file exists and is not empty
    if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
        print("[!] Download appeared to succeed but the file is missing or empty.")
        return None

    size_kb = os.path.getsize(file_path) / 1024
    print(f"[+] OUI list saved successfully ({size_kb:.0f} KB)")
    return os.path.abspath(file_path)


def main():
    parser = argparse.ArgumentParser(
        description="Download the Wireshark OUI manufacturer database for D.A.R.T."
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_FILE,
        help=f"Output file path (default: {DEFAULT_FILE})"
    )
    parser.add_argument(
        "--url",
        default=OUI_URL,
        help=f"URL to download from (default: {OUI_URL})"
    )
    args = parser.parse_args()

    result = download_oui_list(url=args.url, file_path=args.output)
    if result is None:
        sys.exit(1)

    print(f"\n[+] Done. Now run DroneNicList.py to extract drone OUI prefixes.")


if __name__ == "__main__":
    main()
