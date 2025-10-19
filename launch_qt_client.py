#!/usr/bin/env python3
"""
Launcher script for the Qt API client
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Main launcher function"""
    # Get the path to the qt client launcher
    qt_client_launcher = Path(__file__).parent / "src" / "qt_client" / "launcher.py"
    
    if not qt_client_launcher.exists():
        print("Error: Qt client not found at expected location")
        print(f"Expected: {qt_client_launcher}")
        return 1
    
    # Launch the Qt client
    try:
        subprocess.run([sys.executable, str(qt_client_launcher)])
        return 0
    except Exception as e:
        print(f"Error launching Qt client: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
