"""
Example demonstrating device emulator with configuration files
"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shared.utils.config_loader import ConfigLoader
from device_emulator.core.emulator import DeviceEmulator


async def demo_emulator_with_config(config_file: str, duration: int = 10):
    """Demonstrate emulator with a specific configuration file"""
    
    print(f"\n{'='*60}")
    print(f"DEMO: {config_file}")
    print(f"{'='*60}")
    
    # Load configuration
    config_path = Path("config/device_configs") / config_file
    if not config_path.exists():
        print(f"Configuration file not found: {config_path}")
        return
    
    try:
        device_config = ConfigLoader.load_device_config(config_path)
        print(f"Device: {device_config.device_name} ({device_config.device_id})")
        print(f"Type: {device_config.device_type}")
        print(f"Data types: {[dc.name for dc in device_config.data_configs]}")
        print()
        
        # Show configuration details
        for data_config in device_config.data_configs:
            print(f"  {data_config.name}:")
            print(f"    Type: {data_config.data_type}")
            print(f"    Range: {data_config.min_value} - {data_config.max_value} {data_config.unit}")
            print(f"    Frequency: {data_config.frequency} Hz")
            print(f"    Change step: {data_config.change_step}")
            print(f"    Noise: {data_config.noise_level * 100:.1f}%")
            print(f"    Drift: {data_config.drift_rate}")
            print()
        
        # Create emulator
        emulator = DeviceEmulator(device_config)
        
        print("Generating data...")
        print("-" * 40)
        
        # Generate data for specified duration
        for i in range(duration):
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
            
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Main demo function"""
    
    print("Device Emulator Configuration Demo")
    print("This demo shows how to use different device configurations")
    
    # List available configurations
    config_dir = Path("config/device_configs")
    config_files = ConfigLoader.list_config_files(config_dir)
    
    if not config_files:
        print("No configuration files found. Creating example...")
        # Create an example configuration
        from shared.models.device_config import DeviceConfig, DataGenerationConfig, DataType
        
        example_config = DeviceConfig(
            device_id="demo_sensor_001",
            device_name="Demo Sensor",
            device_type="sensor",
            data_configs=[
                DataGenerationConfig(
                    name="temperature",
                    data_type=DataType.FLOAT,
                    min_value=20.0,
                    max_value=30.0,
                    frequency=1.0,
                    change_step=0.2,
                    unit="°C",
                    initial_value=25.0,
                    noise_level=0.01
                )
            ],
            communication={"protocol": "tcp", "port": 8080}
        )
        
        ConfigLoader.save_device_config(example_config, "config/device_configs/demo_sensor.yaml")
        print("Created demo_sensor.yaml")
        config_files = [Path("config/device_configs/demo_sensor.yaml")]
    
    # Demo each configuration
    for config_file in config_files:
        await demo_emulator_with_config(config_file.name, duration=5)
    
    print(f"\n{'='*60}")
    print("Demo completed!")
    print("You can create your own configurations or modify existing ones.")
    print("Use: python -m device_emulator.main --create-example sensor")
    print("Or: python -m device_emulator.main --list-configs")


if __name__ == "__main__":
    asyncio.run(main())
