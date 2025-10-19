"""
Basic device emulator example
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
from device_emulator.core.emulator import DeviceEmulator
from device_emulator.simulators.sensor_simulator import SensorSimulator


async def main():
    """Run a basic device emulator example"""
    
    # Create a sensor simulator
    simulator = SensorSimulator(
        device_id="sensor_001",
        device_type="temperature_sensor",
        sampling_rate=1.0  # 1 Hz
    )
    
    # Create device emulator
    emulator = DeviceEmulator(simulator)
    
    print("Starting device emulator...")
    print(f"Device ID: {simulator.device_id}")
    print(f"Device Type: {simulator.device_type}")
    print(f"Sampling Rate: {simulator.sampling_rate} Hz")
    print("-" * 40)
    
    try:
        # Run for 10 seconds
        for i in range(10):
            # Generate data
            data = await emulator.generate_data()
            
            # Print data
            print(f"Time: {data.timestamp}")
            print(f"Data: {json.dumps(data.data, indent=2)}")
            print("-" * 40)
            
            # Wait for next sample
            await asyncio.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nStopping emulator...")
    
    print("Emulator stopped.")


if __name__ == "__main__":
    asyncio.run(main())
