"""
Simple device emulator demo without external dependencies
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Union, Dict, Any


class SimpleDataGenerator:
    """Simple data generator for demonstration"""
    
    def __init__(self, name: str, data_type: str, min_val: float, max_val: float, 
                 change_step: float, unit: str = "", initial_val: float = None):
        self.name = name
        self.data_type = data_type
        self.min_val = min_val
        self.max_val = max_val
        self.change_step = change_step
        self.unit = unit
        self.current_value = initial_val if initial_val is not None else random.uniform(min_val, max_val)
        self.last_update = datetime.now()
    
    async def generate_next_value(self) -> Union[int, float, str, bool]:
        """Generate next value with controlled change"""
        now = datetime.now()
        time_delta = now - self.last_update
        max_change = self.change_step * time_delta.total_seconds()
        
        if self.data_type == "float":
            change = random.uniform(-max_change, max_change)
            new_value = self.current_value + change
            new_value = max(self.min_val, min(self.max_val, new_value))
            self.current_value = new_value
            return round(new_value, 2)
        
        elif self.data_type == "integer":
            change = random.uniform(-max_change, max_change)
            new_value = self.current_value + change
            new_value = max(self.min_val, min(self.max_val, new_value))
            self.current_value = new_value
            return int(new_value)
        
        elif self.data_type == "boolean":
            flip_probability = min(1.0, self.change_step * time_delta.total_seconds())
            if random.random() < flip_probability:
                self.current_value = not self.current_value
            return bool(self.current_value)
        
        elif self.data_type == "string":
            change_probability = min(1.0, self.change_step * time_delta.total_seconds())
            if random.random() < change_probability:
                states = ["idle", "running", "error", "maintenance"]
                self.current_value = random.choice(states)
            return str(self.current_value)
        
        self.last_update = now
        return self.current_value


class SimpleDeviceEmulator:
    """Simple device emulator for demonstration"""
    
    def __init__(self, device_id: str, device_name: str):
        self.device_id = device_id
        self.device_name = device_name
        self.generators: Dict[str, SimpleDataGenerator] = {}
    
    def add_data_type(self, name: str, data_type: str, min_val: float, max_val: float,
                     change_step: float, unit: str = "", initial_val: float = None):
        """Add a data type to generate"""
        generator = SimpleDataGenerator(name, data_type, min_val, max_val, change_step, unit, initial_val)
        self.generators[name] = generator
        print(f"Added data type: {name} ({data_type}) - Range: {min_val}-{max_val} {unit}")
    
    async def generate_data(self) -> Dict[str, Any]:
        """Generate data for all configured types"""
        data = {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "timestamp": datetime.now().isoformat(),
            "data": {}
        }
        
        for name, generator in self.generators.items():
            value = await generator.generate_next_value()
            data["data"][name] = {
                "value": value,
                "unit": generator.unit,
                "type": generator.data_type
            }
        
        return data


async def demo_temperature_sensor():
    """Demo temperature sensor with multiple data types"""
    
    print("=" * 60)
    print("TEMPERATURE SENSOR DEMO")
    print("=" * 60)
    
    # Create emulator
    emulator = SimpleDeviceEmulator("temp_sensor_001", "Temperature Sensor")
    
    # Add data types
    emulator.add_data_type("temperature", "float", -40.0, 85.0, 0.5, "°C", 20.0)
    emulator.add_data_type("humidity", "float", 0.0, 100.0, 1.0, "%", 50.0)
    emulator.add_data_type("status", "boolean", 0, 1, 0.01, "", True)
    emulator.add_data_type("alarm_count", "integer", 0, 10, 0.1, "", 0)
    
    print(f"\nDevice: {emulator.device_name} ({emulator.device_id})")
    print("Generating data for 10 seconds...\n")
    
    # Generate data for 10 seconds
    for i in range(10):
        data = await emulator.generate_data()
        
        print(f"Sample {i+1} at {data['timestamp'][:19]}:")
        for name, info in data["data"].items():
            print(f"  {name}: {info['value']} {info['unit']} ({info['type']})")
        print()
        
        await asyncio.sleep(1.0)


async def demo_motor_controller():
    """Demo motor controller with different data types"""
    
    print("=" * 60)
    print("MOTOR CONTROLLER DEMO")
    print("=" * 60)
    
    # Create emulator
    emulator = SimpleDeviceEmulator("motor_001", "Motor Controller")
    
    # Add data types
    emulator.add_data_type("rpm", "integer", 0, 3000, 50, "RPM", 0)
    emulator.add_data_type("temperature", "float", 20.0, 80.0, 2.0, "°C", 25.0)
    emulator.add_data_type("status", "string", 0, 1, 0.05, "", "idle")
    emulator.add_data_type("power_on", "boolean", 0, 1, 0.001, "", True)
    
    print(f"\nDevice: {emulator.device_name} ({emulator.device_id})")
    print("Generating data for 8 seconds...\n")
    
    # Generate data for 8 seconds
    for i in range(8):
        data = await emulator.generate_data()
        
        print(f"Sample {i+1} at {data['timestamp'][:19]}:")
        for name, info in data["data"].items():
            print(f"  {name}: {info['value']} {info['unit']} ({info['type']})")
        print()
        
        await asyncio.sleep(1.0)


async def main():
    """Main demo function"""
    
    print("SIMPLE DEVICE EMULATOR DEMO")
    print("This demo shows how the device emulator generates various data types")
    print("with configurable parameters like frequency, change steps, and ranges.\n")
    
    # Demo temperature sensor
    await demo_temperature_sensor()
    
    # Demo motor controller
    await demo_motor_controller()
    
    print("=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)
    print("\nKey Features Demonstrated:")
    print("• Multiple data types: float, integer, boolean, string")
    print("• Configurable ranges and change steps")
    print("• Realistic value changes over time")
    print("• Different generation frequencies")
    print("• Units and metadata support")
    print("\nThe full emulator supports:")
    print("• YAML/JSON configuration files")
    print("• Noise and drift simulation")
    print("• Communication protocols")
    print("• Extensible data generators")


if __name__ == "__main__":
    asyncio.run(main())
