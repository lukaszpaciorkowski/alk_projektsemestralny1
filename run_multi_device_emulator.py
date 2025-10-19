#!/usr/bin/env python3
"""
Script to run the multi-device emulator with unified configuration
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from shared.utils.config_loader import ConfigLoader
from device_emulator.core.multi_device_emulator import MultiDeviceEmulator


async def main():
    """Main function for multi-device emulator"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Multi-Device Emulator")
    parser.add_argument("--config", "-c", type=str, 
                       default="config/unified_device_config.yaml",
                       help="Path to unified device configuration file")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--base-port", type=int, default=8080, 
                       help="Base port number (devices will use base_port + index)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--duration", type=int, default=10, help="Duration to run in seconds")
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
        return
    
    try:
        multi_config = ConfigLoader.load_multi_device_config(config_path)
        logger.info(f"Loaded configuration: {multi_config.config_name}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return
    
    # Handle special commands
    if args.list_devices:
        print(f"\nConfiguration: {multi_config.config_name}")
        print(f"Description: {multi_config.description}")
        print(f"Total devices: {len(multi_config.devices)}")
        print("\nDevices:")
        for device in multi_config.devices:
            print(f"  - {device.device_id}: {device.device_name} ({device.device_type.value})")
            print(f"    Location: {device.metadata.location}")
            print(f"    Data types: {[dc.name for dc in device.data_configs]}")
        return
    
    if args.device_info:
        device_def = multi_config.get_device_by_id(args.device_info)
        if not device_def:
            print(f"Device {args.device_info} not found")
            return
        
        print(f"\nDevice Information: {args.device_info}")
        print("=" * 50)
        print(f"Name: {device_def.device_name}")
        print(f"Type: {device_def.device_type.value}")
        print(f"Location: {device_def.metadata.location}")
        print(f"Manufacturer: {device_def.metadata.manufacturer}")
        print(f"Model: {device_def.metadata.model}")
        print(f"Serial Number: {device_def.metadata.serial_number}")
        print(f"Installation Date: {device_def.metadata.installation_date}")
        print(f"Maintenance Schedule: {device_def.metadata.maintenance_schedule}")
        print(f"Environment: {device_def.metadata.environment}")
        print(f"Notes: {device_def.metadata.notes}")
        print(f"Communication Port: {device_def.communication.get('port', 'default')}")
        print("\nData Types:")
        for data_config in device_def.data_configs:
            print(f"  - {data_config.name}: {data_config.data_type.value} ({data_config.unit})")
            print(f"    Range: {data_config.min_value} - {data_config.max_value}")
            print(f"    Frequency: {data_config.frequency} Hz")
            print(f"    Change Step: {data_config.change_step}")
        print("\nCustom Fields:")
        for key, value in device_def.metadata.custom_fields.items():
            print(f"  - {key}: {value}")
        return
    
    # Create multi-device emulator
    emulator = MultiDeviceEmulator(multi_config)
    
    logger.info("Starting multi-device emulator...")
    logger.info(f"Configuration: {multi_config.config_name}")
    logger.info(f"Devices: {len(multi_config.devices)}")
    
    # Show device summary
    print(f"\n{'='*60}")
    print(f"MULTI-DEVICE EMULATOR: {multi_config.config_name}")
    print(f"{'='*60}")
    print(f"Description: {multi_config.description}")
    print(f"Total Devices: {len(multi_config.devices)}")
    print(f"Duration: {args.duration} seconds")
    print(f"Host: {args.host}")
    print(f"Base Port: {args.base_port}")
    
    # Show devices
    print(f"\nDevices:")
    for i, device in enumerate(multi_config.devices):
        port = args.base_port + i
        if 'port' in device.communication:
            port = device.communication['port']
        print(f"  {i+1}. {device.device_name} ({device.device_id})")
        print(f"     Type: {device.device_type.value}")
        print(f"     Location: {device.metadata.location}")
        print(f"     Port: {port}")
        print(f"     Data Types: {[dc.name for dc in device.data_configs]}")
    
    print(f"\nGenerating data for {args.duration} seconds...")
    print("=" * 60)
    
    try:
        # Run for specified duration
        for i in range(args.duration):
            print(f"\n--- Sample {i+1} ---")
            
            if args.device:
                # Generate data for specific device only
                device_info = emulator.get_device_info(args.device)
                if device_info:
                    print(f"Device: {device_info['device_name']} ({args.device})")
                    for data_type_name in device_info['data_types']:
                        data = await emulator.generate_data_for_device(args.device, data_type_name)
                        if data:
                            timestamp = data.timestamp.strftime('%H:%M:%S.%f')[:-3]
                            print(f"  {data.data_type}: {data.value} {data.unit} (at {timestamp})")
                else:
                    print(f"Device {args.device} not found")
            else:
                # Generate data for all devices
                all_data = await emulator.generate_data_for_all_devices()
                
                for device_id, device_data in all_data.items():
                    device_info = emulator.get_device_info(device_id)
                    if device_info:
                        print(f"\n{device_info['device_name']} ({device_id}):")
                        for data_type_name, data in device_data.items():
                            timestamp = data.timestamp.strftime('%H:%M:%S.%f')[:-3]
                            print(f"  {data.data_type}: {data.value} {data.unit} (at {timestamp})")
            
            # Wait for next sample
            await asyncio.sleep(1.0)
        
        print("\n" + "=" * 60)
        print("Multi-device emulator completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Stopping emulator...")
        await emulator.stop()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
    finally:
        logger.info("Multi-device emulator stopped.")


if __name__ == "__main__":
    asyncio.run(main())
