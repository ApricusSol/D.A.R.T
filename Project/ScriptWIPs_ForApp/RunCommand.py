"""Function that executes a legacy shell command silently, suppressing stdout and stderr."""

import subprocess

def run_command(command):
    subprocess.run(command, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)