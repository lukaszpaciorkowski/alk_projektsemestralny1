#!/usr/bin/env python3
"""
Example REST API client for device emulator
"""

import asyncio
import aiohttp
import json
from datetime import datetime


class DeviceEmulatorClient:
    """Client for interacting with device emulator REST API"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
    
    async def health_check(self) -> dict:
        """Check if the API is healthy"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                return await response.json()
    
    async def get_all_devices(self) -> dict:
        """Get information about all devices"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/devices") as response:
                return await response.json()
    
    async def get_device_info(self, device_id: str) -> dict:
        """Get information about a specific device"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/devices/{device_id}") as response:
                return await response.json()
    
    async def get_all_data(self) -> dict:
        """Get current data from all devices"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/data") as response:
                return await response.json()
    
    async def get_device_data(self, device_id: str) -> dict:
        """Get current data from a specific device"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/data/{device_id}") as response:
                return await response.json()
    
    async def get_specific_data(self, device_id: str, data_type: str) -> dict:
        """Get specific data type from a specific device"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/data/{device_id}/{data_type}") as response:
                return await response.json()
    
    async def monitor_device(self, device_id: str, duration: int = 10):
        """Monitor a device for a specified duration"""
        print(f"Monitoring device {device_id} for {duration} seconds...")
        
        for i in range(duration):
            try:
                data = await self.get_device_data(device_id)
                if 'data' in data:
                    print(f"\n--- Sample {i+1} ---")
                    for data_type, values in data['data'].items():
                        print(f"{data_type}: {values['value']} {values['unit']} (at {values['timestamp']})")
                else:
                    print(f"Error: {data.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error: {e}")
            
            await asyncio.sleep(1.0)
    
    async def monitor_all_devices(self, duration: int = 10):
        """Monitor all devices for a specified duration"""
        print(f"Monitoring all devices for {duration} seconds...")
        
        for i in range(duration):
            try:
                data = await self.get_all_data()
                if 'data' in data:
                    print(f"\n--- Sample {i+1} ---")
                    for device_id, device_data in data['data'].items():
                        print(f"\n{device_id}:")
                        for data_type, values in device_data.items():
                            print(f"  {data_type}: {values['value']} {values['unit']}")
                else:
                    print(f"Error: {data.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"Error: {e}")
            
            await asyncio.sleep(1.0)


async def main():
    """Example usage of the REST API client"""
    
    client = DeviceEmulatorClient()
    
    print("Device Emulator REST API Client Example")
    print("=" * 50)
    
    try:
        # Check if API is healthy
        print("\n1. Checking API health...")
        health = await client.health_check()
        print(f"   Status: {health.get('status', 'unknown')}")
        print(f"   Emulator: {health.get('emulator', 'unknown')}")
        
        # Get all devices
        print("\n2. Getting all devices...")
        devices = await client.get_all_devices()
        print(f"   Total devices: {devices.get('count', 0)}")
        for device_id, device_info in devices.get('devices', {}).items():
            print(f"   - {device_id}: {device_info.get('device_name', 'Unknown')}")
        
        # Get specific device info
        print("\n3. Getting device info...")
        device_id = "temp_sensor_001"
        device_info = await client.get_device_info(device_id)
        if 'device' in device_info:
            device = device_info['device']
            print(f"   Device: {device.get('device_name', 'Unknown')}")
            print(f"   Type: {device.get('device_type', 'Unknown')}")
            print(f"   Location: {device.get('metadata', {}).get('location', 'Unknown')}")
        
        # Get current data from all devices
        print("\n4. Getting current data from all devices...")
        all_data = await client.get_all_data()
        if 'data' in all_data:
            for device_id, device_data in all_data['data'].items():
                print(f"   {device_id}:")
                for data_type, values in device_data.items():
                    print(f"     {data_type}: {values['value']} {values['unit']}")
        
        # Monitor a specific device
        print("\n5. Monitoring specific device...")
        await client.monitor_device("temp_sensor_001", duration=3)
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the device emulator is running with REST API enabled!")


if __name__ == "__main__":
    asyncio.run(main())
