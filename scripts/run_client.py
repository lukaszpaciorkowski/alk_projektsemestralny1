#!/usr/bin/env python3
"""
Script to run the Qt client
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client.main import main

if __name__ == "__main__":
    main()
