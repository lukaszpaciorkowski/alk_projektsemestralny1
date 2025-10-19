#!/usr/bin/env python3
"""
Script to run the device emulator with proper imports
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared.utils.config_loader import ConfigLoader
from device_emulator.core.emulator import DeviceEmulator


async def main():
    """Main function for device emulator"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Device Emulator")
    parser.add_argument("--config", "-c", type=str, help="Path to device configuration file")
    parser.add_argument("--device-id", help="Device ID (overrides config)")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, help="Port to bind to (overrides config)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--list-configs", action="store_true", help="List available configuration files")
    # parser.add_argument("--create-example", choices=["sensor", "actuator"], help="Create example configuration")
    parser.add_argument("--duration", type=int, default=10, help="Duration to run in seconds")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    
    # Handle special commands
    if args.list_configs:
        config_dir = Path("config/device_configs")
        config_files = ConfigLoader.list_config_files(config_dir)
        if config_files:
            print("Available configuration files:")
            for config_file in config_files:
                print(f"  - {config_file}")
        else:
            print("No configuration files found in config/device_configs/")
        return
    
    # if args.create_example:
    #     config = ConfigLoader.create_example_config(args.create_example)
    #     output_file = f"config/device_configs/example_{args.create_example}.yaml"
    #     ConfigLoader.save_device_config(config, output_file)
    #     print(f"Created example configuration: {output_file}")
    #     return
    
    # Load device configuration
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return
        
        try:
            device_config = ConfigLoader.load_device_config(config_path)
            logger.info(f"Loaded configuration from: {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return
    else:
        # Use default configuration
        default_config_path = Path("config/device_configs/temperature_sensor.yaml")
        if default_config_path.exists():
            try:
                device_config = ConfigLoader.load_device_config(default_config_path)
                logger.info(f"Using default configuration: {default_config_path}")
            except Exception as e:
                logger.error(f"Error loading default configuration: {e}")
                return
        else:
            logger.error("No configuration file provided and no default configuration found")
            logger.info("Use --create-example sensor to create an example configuration")
            return
    
    # Override configuration with command line arguments
    if args.device_id:
        device_config.device_id = args.device_id
    
    if args.port:
        device_config.communication["port"] = args.port
    
    logger.info("Starting device emulator...")
    logger.info(f"Device: {device_config.device_name} ({device_config.device_id})")
    logger.info(f"Data types: {[dc.name for dc in device_config.data_configs]}")
    
    try:
        # Create emulator
        emulator = DeviceEmulator(device_config)
        
        # Run for specified duration
        print(f"\nGenerating data for {args.duration} seconds...")
        print("=" * 60)
        
        for i in range(args.duration):
            print(f"\nSample {i+1}:")
            
            # Generate data for each configured data type
            for data_type_name in emulator.get_available_data_types():
                data = await emulator.generate_single_data(data_type_name)
                if data:
                    timestamp = data.timestamp.strftime('%H:%M:%S.%f')[:-3]
                    print(f"  {data.data_type}: {data.value} {data.unit} (at {timestamp})")
            
            # Show current values
            current_values = emulator.get_current_values()
            print(f"  Current values: {current_values}")
            
            # Wait for next sample
            await asyncio.sleep(1.0)
        
        print("\n" + "=" * 60)
        print("Emulator completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Stopping emulator...")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        logger.info("Emulator stopped.")


if __name__ == "__main__":
    asyncio.run(main())
