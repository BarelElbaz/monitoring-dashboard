#!/usr/bin/env python3
import os
import platform
import subprocess
import shutil

def build_executable():
    # Determine the platform
    system = platform.system().lower()
    
    # Set the data separator based on platform
    separator = ';' if system == 'windows' else ':'
    
    # Base PyInstaller command
    cmd = [
        'pyinstaller',
        '--clean',    # Clean PyInstaller cache
        '--log-level=INFO',
        '--name=monitoring-dashboard',  # Name of the executable
    ]
    
    # Add platform-specific options
    if system == 'darwin':  # macOS
        cmd.extend([
            '--windowed',  # Prevent terminal window from appearing
            '--icon=base_icon.png',  # Use the base icon
        ])
    elif system == 'windows':
        cmd.extend([
            '--noconsole',  # Prevent console window from appearing
            '--icon=base_icon.png',  # Use the base icon
        ])
    elif system == 'linux':
        cmd.extend([
            '--icon=base_icon.png',  # Use the base icon
        ])
    
    # Add the main script
    cmd.append('monitoring-dashboard.py')
    
    # Run PyInstaller
    print(f"Building executable for {system}...")
    print(f"Command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    # Copy config.json next to the app bundle
    if system == 'darwin':
        app_path = os.path.join('dist', 'monitoring-dashboard.app')
        if os.path.exists(app_path):
            config_dest = os.path.dirname(app_path)
            shutil.copy2('config.json', config_dest)
    else:
        # For other platforms, copy next to the executable
        shutil.copy2('config.json', 'dist')
    
    print(f"\nBuild complete! Executable is in the 'dist' directory.")
    print("Make sure to distribute config.json along with the executable.")

if __name__ == '__main__':
    build_executable()
