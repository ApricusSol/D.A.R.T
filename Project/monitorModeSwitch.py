#!/usr/bin/env python3
"""
This script automates the process of switching a wireless network adapter into monitor mode and capturing packets using the Wireshark. When the script is stopped, it saves the capture to the desktop, log actions to a text file, and restores the adapter to managed mode.


Things to note -

My Intel iwlwifi driver fails to capture packets when the primary managed interface is directly switched to monitor mode. This means to get it working, it requires a secondary virtual interface. Replacing the manual iw commands and using airmon-ng will automatically create a dedicated virtual interface (wlan0mon) compatible with the Intel driver. This fixes issues with not having data show up in monitor mode. This will likely need to be changed (along with the BASE_INTERFACE variable when using different adapters.

When ran, the error "GUI WARNING] -- Failed to register with host portal QDBusError("org.freedesktop.portal.Error.Failed", "Could not register app ID: Connection already associated with an application ID")" may appear. This is a non-fatal warning syaing that Wireshark's GUI failed to register with the Linux desktop's D-Bus session management (XDG Desktop Portal. This error commonly occurs when a GUI application is launched from a script or when switching user privileges which causes a mismatch in session environment variables. This error does not affect packet capture functionality and can be safely ignored.

"""

import subprocess
import sys
import os
import datetime

""" set config constants """
BASE_INTERFACE = "wlan0"
MON_INTERFACE = "wlan0mon"
ACTUAL_USER = os.environ.get("SUDO_USER", "user") 
DESKTOP_PATH = f"/home/{ACTUAL_USER}/Desktop"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
CAPTURE_FILE = os.path.join(DESKTOP_PATH, f"capture_{TIMESTAMP}.pcapng")
LOG_FILE = os.path.join(DESKTOP_PATH, f"log_{TIMESTAMP}.txt")

def log_action(action):
    """Append timestamped action message to log file."""
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
    """Run a shell command silently suppressing stdout and stderr so terminal doesn't get jumbled"""
    subprocess.run(command, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def enable_monitor_mode():
    """Stops potentially interfering processes and uses airmon-ng to create a virtual monitor interface."""
    log_action("Killing interfering network processes (airmon-ng check kill)...")
    run_command("airmon-ng check kill")

    log_action("Removing any software blocks on the radio...")
    run_command("rfkill unblock wifi")
    
    log_action(f"Starting virtual monitor interface on {BASE_INTERFACE}...")
    run_command(f"airmon-ng start {BASE_INTERFACE}")
    
    log_action(f"Tuning {MON_INTERFACE} to channel 6...")
    run_command(f"iw dev {MON_INTERFACE} set channel 6")
    
    log_action(f"{MON_INTERFACE} is now active and tuned to channel 6.")

def disable_monitor_mode():
    """Stops the virtual monitor interface and restores network services."""
    log_action(f"Stopping virtual monitor interface {MON_INTERFACE}...")
    run_command(f"airmon-ng stop {MON_INTERFACE}")
    
    log_action("Restarting NetworkManager service to restore internet connectivity...")
    run_command("systemctl restart NetworkManager")
    
    log_action(f"Adapter restored to managed mode and network services restarted.")

def main():
    if os.geteuid() != 0:
        sys.exit("This script must be run as root (sudo).")
        
    log_action("Script execution started.")
    
    enable_monitor_mode()
    
    log_action(f"Launching Wireshark GUI on {MON_INTERFACE}. Capture file: {CAPTURE_FILE}")
    
    process = subprocess.Popen([
        "sudo", "-u", ACTUAL_USER, 
        "wireshark", 
        "-i", MON_INTERFACE, 
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
