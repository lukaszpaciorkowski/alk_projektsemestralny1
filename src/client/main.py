"""
Main entry point for the Qt client
"""

import sys
import argparse
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .ui.main_window import MainWindow


def main():
    """Main function for Qt client"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Qt Client for Device Emulator")
    parser.add_argument("--host", default="localhost", help="Emulator host")
    parser.add_argument("--port", type=int, default=8080, help="Emulator port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Qt client...")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Device Emulator Client")
    app.setApplicationVersion("0.1.0")
    
    try:
        # Create main window
        window = MainWindow(host=args.host, port=args.port)
        window.show()
        
        logger.info("Qt client started successfully")
        
        # Run application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
