#!/usr/bin/env python3
"""
Script to run the simplified single-threaded emulator
"""

import sys
import asyncio
import argparse
import logging
import signal
import threading
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared.utils.config_loader import ConfigLoader
from device_emulator.core.simple_emulator import SimpleEmulator


class EmulatorRunner:
    """Simple runner for the emulator without asyncio in main thread"""
    
    def __init__(self, config, host="localhost", api_port=8080, enable_api=True, duration=None):
        self.config = config
        self.host = host
        self.api_port = api_port
        self.enable_api = enable_api
        self.duration = duration
        self.emulator = None
        self.running = False
        self.stop_event = threading.Event()
        
    def start(self):
        """Start the emulator in a separate thread"""
        self.running = True
        self.emulator = SimpleEmulator(self.config)
        
        # Set callback to notify when emulator stops
        self.emulator.external_stop_callback = self._on_emulator_stop
        
        # Start emulator in a separate thread
        self.emulator_thread = threading.Thread(target=self._run_emulator)
        self.emulator_thread.daemon = True
        self.emulator_thread.start()
        
        # Wait for emulator to start
        time.sleep(1)
    
    def _on_emulator_stop(self):
        """Callback when emulator stops"""
        self.running = False
        self.stop_event.set()
        
    def _run_emulator(self):
        """Run the emulator in a separate thread"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start the emulator
            if self.duration:
                loop.run_until_complete(
                    asyncio.wait_for(
                        self.emulator.start(
                            host=self.host,
                            api_port=self.api_port,
                            enable_api=self.enable_api
                        ),
                        timeout=self.duration
                    )
                )
            else:
                loop.run_until_complete(
                    self.emulator.start(
                        host=self.host,
                        api_port=self.api_port,
                        enable_api=self.enable_api
                    )
                )
        except asyncio.TimeoutError:
            print(f"Emulator ran for {self.duration} seconds and stopped")
        except Exception as e:
            print(f"Error in emulator: {e}")
        finally:
            self.running = False
            self.stop_event.set()
    
    def stop(self):
        """Stop the emulator"""
        if self.emulator and self.running:
            # Stop the emulator
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.emulator.stop())
            self.running = False
            self.stop_event.set()
    
    def wait_for_stop(self):
        """Wait for the emulator to stop"""
        self.stop_event.wait()


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\nReceived interrupt signal, stopping emulator...")
    if 'runner' in globals():
        runner.stop()
    sys.exit(0)


def main():
    """Main function for simplified emulator"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simplified Device Emulator")
    parser.add_argument("--config", "-c", type=str, 
                       default="config/unified_device_config.yaml",
                       help="Path to unified device configuration file")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--api-port", type=int, default=8080, 
                       help="Port for REST API server")
    parser.add_argument("--no-api", action="store_true", help="Disable REST API server")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--duration", type=int, help="Duration to run in seconds")
    parser.add_argument("--device", type=str, help="Run only specific device ID")
    parser.add_argument("--list-devices", action="store_true", help="List all devices in config")
    parser.add_argument("--device-info", type=str, help="Show detailed info for specific device")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    
    # Load multi-device configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return 1
    
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_multi_device_config(config_path)
        logger.info(f"Loaded configuration: {config.config_name}")
        logger.info(f"Found {len(config.devices)} devices")
        
        # Handle list devices command
        if args.list_devices:
            print("\nAvailable devices:")
            for device in config.devices:
                print(f"  - {device.device_id}: {device.device_name} ({device.device_type.value})")
                for data_config in device.data_configs:
                    print(f"    * {data_config.name}: {data_config.data_type.value} at {data_config.frequency} Hz")
            return 0
        
        # Handle device info command
        if args.device_info:
            device = config.get_device_by_id(args.device_info)
            if not device:
                logger.error(f"Device {args.device_info} not found")
                return 1
            
            print(f"\nDevice Information:")
            print(f"  ID: {device.device_id}")
            print(f"  Name: {device.device_name}")
            print(f"  Type: {device.device_type.value}")
            print(f"  Data Types:")
            for data_config in device.data_configs:
                print(f"    - {data_config.name}: {data_config.data_type.value}")
                print(f"      Range: {data_config.min_value} - {data_config.max_value}")
                print(f"      Frequency: {data_config.frequency} Hz")
                print(f"      Unit: {data_config.unit}")
            return 0
        
        # Filter devices if specific device requested
        if args.device:
            device = config.get_device_by_id(args.device)
            if not device:
                logger.error(f"Device {args.device} not found")
                return 1
            config.devices = [device]
            logger.info(f"Running only device: {device.device_name}")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and start the emulator runner
        global runner
        runner = EmulatorRunner(
            config=config,
            host=args.host,
            api_port=args.api_port,
            enable_api=not args.no_api,
            duration=args.duration
        )
        
        logger.info("Starting simplified emulator...")
        logger.info("Press Ctrl+C to stop or use GET /stop endpoint")
        
        # Start the emulator
        runner.start()
        
        # Wait for emulator to stop
        runner.wait_for_stop()
        
        logger.info("Emulator stopped.")
        return 0
        
    except Exception as e:
        logger.error(f"Error running emulator: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
