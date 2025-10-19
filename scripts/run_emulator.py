#!/usr/bin/env python3
"""
Script to run the device emulator
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from device_emulator.main import main

if __name__ == "__main__":
    asyncio.run(main())
