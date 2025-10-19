#!/usr/bin/env python3
"""
Launcher script for the Qt API client
"""

import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import PyQt6
        import aiohttp
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install dependencies with:")
        print("pip install PyQt6 aiohttp")
        return False

def main():
    """Main launcher function"""
    print("Device Emulator Qt API Client")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Launch the Qt client
    try:
        # Add the qt_client directory to Python path for imports
        qt_client_dir = Path(__file__).parent
        sys.path.insert(0, str(qt_client_dir))
        
        client_script = qt_client_dir / "api_client.py"
        subprocess.run([sys.executable, str(client_script)])
        return 0
    except Exception as e:
        print(f"Error launching Qt client: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
