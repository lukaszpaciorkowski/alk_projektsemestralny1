"""
Basic device emulator example using configuration
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
import sys

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from shared.models.device_data import DeviceData
from shared.models.device_config import DeviceConfig, DataGenerationConfig, DataType
from device_emulator.core.emulator import DeviceEmulator


async def main():
    """Run a basic device emulator example with configuration"""
    
    # Create a device configuration programmatically
    device_config = DeviceConfig(
        device_id="example_sensor_001",
        device_name="Example Temperature Sensor",
        device_type="sensor",
        data_configs=[
            DataGenerationConfig(
                name="temperature",
                data_type=DataType.FLOAT,
                min_value=-40.0,
                max_value=85.0,
                frequency=1.0,  # 1 Hz
                change_step=0.5,  # Max 0.5°C change per second
                unit="°C",
                initial_value=20.0,
                noise_level=0.02,  # 2% noise
                drift_rate=0.001  # 0.001°C per second drift
            ),
            DataGenerationConfig(
                name="humidity",
                data_type=DataType.FLOAT,
                min_value=0.0,
                max_value=100.0,
                frequency=0.5,  # 0.5 Hz
                change_step=1.0,  # Max 1% change per second
                unit="%",
                initial_value=50.0,
                noise_level=0.01,  # 1% noise
                drift_rate=0.0  # No drift
            ),
            DataGenerationConfig(
                name="status",
                data_type=DataType.BOOLEAN,
                min_value=0,
                max_value=1,
                frequency=0.1,  # 0.1 Hz (every 10 seconds)
                change_step=0.01,  # 1% chance to change per second
                unit="",
                initial_value=True,
                noise_level=0.0,
                drift_rate=0.0
            )
        ],
        communication={"protocol": "tcp", "port": 8080},
        metadata={"location": "Example Room", "manufacturer": "ExampleCorp"}
    )
    
    # Create device emulator
    emulator = DeviceEmulator(device_config)
    
    print("Starting device emulator...")
    print(f"Device: {device_config.device_name} ({device_config.device_id})")
    print(f"Data types: {[dc.name for dc in device_config.data_configs]}")
    print("-" * 60)
    
    try:
        # Run for 20 seconds, generating data every second
        for i in range(20):
            print(f"\n--- Sample {i+1} ---")
            
            # Generate data for each configured data type
            for data_type_name in emulator.get_available_data_types():
                data = await emulator.generate_single_data(data_type_name)
                if data:
                    print(f"{data.data_type}: {data.value} {data.unit} (at {data.timestamp.strftime('%H:%M:%S.%f')[:-3]})")
            
            # Show current values
            current_values = emulator.get_current_values()
            print(f"Current values: {current_values}")
            
            # Wait for next sample
            await asyncio.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nStopping emulator...")
    
    print("Emulator stopped.")


if __name__ == "__main__":
    asyncio.run(main())
