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
    """Kills interfering processes, brings interface down, switches to monitor mode, and brings it up."""
    log_action("Killing interfering network processes (airmon-ng check kill)...")
    run_command("airmon-ng check kill")

    log_action(f"Setting {INTERFACE} down...")
    run_command(f"ip link set {INTERFACE} down")
    
    log_action(f"Switching {INTERFACE} to monitor mode...")
    run_command(f"iw dev {INTERFACE} set type monitor")
    
    log_action(f"Bringing {INTERFACE} up...")
    run_command(f"ip link set {INTERFACE} up")
    log_action(f"{INTERFACE} is now in monitor mode.")

def disable_monitor_mode():
    """Brings interface down, switches to managed mode, brings it up, and restores network services."""
    log_action(f"Setting {INTERFACE} down...")
    run_command(f"ip link set {INTERFACE} down")
    
    log_action(f"Switching {INTERFACE} to managed mode...")
    run_command(f"iw dev {INTERFACE} set type managed")
    
    log_action(f"Bringing {INTERFACE} up...")
    run_command(f"ip link set {INTERFACE} up")
    
    log_action("Restarting NetworkManager service to restore internet connectivity...")
    run_command("systemctl restart NetworkManager")
    
    log_action(f"{INTERFACE} has been restored to managed mode and network services restarted.")

def main():
    if os.geteuid() != 0:
        sys.exit("This script must be run as root (sudo).")
        
    log_action("Script execution started.")
    
    enable_monitor_mode()
    
    log_action(f"Launching Wireshark GUI. Capture file will be saved to: {CAPTURE_FILE}")
    
    # Removed the -I flag. Since the script already manually set monitor mode as root, 
    # unprivileged Wireshark doesn't need to (and doesn't have permission to) set it again.
    # The -p flag is kept to prevent Wireshark from attempting to set promiscuous mode.
    process = subprocess.Popen([
        "sudo", "-u", ACTUAL_USER, 
        "wireshark", 
        "-i", INTERFACE, 
        "-p", 
        "-k", 
        "-w", CAPTURE_FILE
    ])
    
    try:
        process.wait()
        log_action("Capture process terminated by user.")
    except KeyboardInterrupt:
        log_action("Keyboard interrupt detected. Terminating capture.")
        process.terminate()
        process.wait()
    finally:
        disable_monitor_mode()
        
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
