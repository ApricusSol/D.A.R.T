#!/usr/bin/env python3
"""
This script automates the process of switching a wireless network adapter into monitor mode capturing packets using the Wireshark GUI, saving the capture to the desktop, log actions to a text file, and restore the adapter to managed mode upon termination.
"""

import subprocess
import sys
import os
import datetime

# Configuration constants
INTERFACE = "wlan0"
# Get the original user who ran sudo to avoid root restriction errors, default to 'user'
ACTUAL_USER = os.environ.get("SUDO_USER", "user") 
DESKTOP_PATH = f"/home/{ACTUAL_USER}/Desktop"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
CAPTURE_FILE = os.path.join(DESKTOP_PATH, f"capture_{TIMESTAMP}.pcapng")
LOG_FILE = os.path.join(DESKTOP_PATH, f"log_{TIMESTAMP}.txt")

def log_action(action):
    """Appends a timestamped action message to the log file."""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{current_time}] {action}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_message)
    
    # Ensure the log file is owned by the actual user if created by root
    try:
        uid = int(subprocess.getoutput(f"id -u {ACTUAL_USER}"))
        gid = int(subprocess.getoutput(f"id -g {ACTUAL_USER}"))
        os.chown(LOG_FILE, uid, gid)
    except Exception:
        pass

def run_command(command):
    """Executes a shell command silently, suppressing stdout and stderr."""
    subprocess.run(command, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def enable_monitor_mode():
    """Brings the interface down, switches it to monitor mode, and brings it back up."""
    log_action(f"Setting {INTERFACE} down...")
    run_command(f"ip link set {INTERFACE} down")
    
    log_action(f"Switching {INTERFACE} to monitor mode...")
    run_command(f"iw dev {INTERFACE} set type monitor")
    
    log_action(f"Bringing {INTERFACE} up...")
    run_command(f"ip link set {INTERFACE} up")
    log_action(f"{INTERFACE} is now in monitor mode.")

def disable_monitor_mode():
    """Brings the interface down, switches it back to managed mode, and brings it back up."""
    log_action(f"Setting {INTERFACE} down...")
    run_command(f"ip link set {INTERFACE} down")
    
    log_action(f"Switching {INTERFACE} to managed mode...")
    run_command(f"iw dev {INTERFACE} set type managed")
    
    log_action(f"Bringing {INTERFACE} up...")
    run_command(f"ip link set {INTERFACE} up")
    log_action(f"{INTERFACE} has been restored to managed mode.")

def main():
    # Ensure the script is executed with root privileges
    if os.geteuid() != 0:
        sys.exit("This script must be run as root (sudo).")
        
    log_action("Script execution started.")
    
    # Switch the network adapter to monitor mode
    enable_monitor_mode()
    
    log_action(f"Launching Wireshark GUI. Capture file will be saved to: {CAPTURE_FILE}")
    
    # Launch Wireshark as the standard user to bypass root GUI and permission restrictions
    process = subprocess.Popen(["sudo", "-u", ACTUAL_USER, "wireshark", "-i", INTERFACE, "-k", "-w", CAPTURE_FILE])
    
    try:
        # Wait for the Wireshark process to complete or be interrupted
        process.wait()
        log_action("Capture process terminated by user.")
    except KeyboardInterrupt:
        # Handle Ctrl+C to cleanly stop the capture before restoring adapter state
        log_action("Keyboard interrupt detected. Terminating capture.")
        process.terminate()
        process.wait()
    finally:
        # Always ensure the adapter is restored to managed mode before exiting
        disable_monitor_mode()
        
        # Ensure capture file is owned by standard user if created by root
        try:
            uid = int(subprocess.getoutput(f"id -u {ACTUAL_USER}"))
            gid = int(subprocess.getoutput(f"id -g {ACTUAL_USER}"))
            if os.path.exists(CAPTURE_FILE):
                os.chown(CAPTURE_FILE, uid, gid)
        except Exception:
            pass
            
        log_action("Script execution finished. Adapter restored.")

if __name__ == "__main__":
    main()
