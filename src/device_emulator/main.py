"""
Main entry point for the device emulator
"""

import asyncio
import argparse
import logging
from pathlib import Path

from .core.emulator import DeviceEmulator
from .simulators.sensor_simulator import SensorSimulator


async def main():
    """Main function for device emulator"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Device Emulator")
    parser.add_argument("--device-id", default="sensor_001", help="Device ID")
    parser.add_argument("--device-type", default="temperature_sensor", help="Device type")
    parser.add_argument("--sampling-rate", type=float, default=1.0, help="Sampling rate in Hz")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting device emulator...")
    
    try:
        # Create simulator
        simulator = SensorSimulator(
            device_id=args.device_id,
            device_type=args.device_type,
            sampling_rate=args.sampling_rate
        )
        
        # Create emulator
        emulator = DeviceEmulator(simulator)
        
        # Start emulator
        await emulator.start(host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("Stopping emulator...")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        logger.info("Emulator stopped.")


if __name__ == "__main__":
    asyncio.run(main())
