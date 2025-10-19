"""
Simplified single-threaded emulator
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from shared.models.multi_device_config import MultiDeviceConfig, DeviceDefinition
from shared.models.device_data import DeviceData
from .simple_device import SimpleDevice
from ..api.rest_server import RestApiServer


class SimpleEmulator:
    """Simplified single-threaded emulator that manages all devices in one loop"""
    
    def __init__(self, config: MultiDeviceConfig):
        self.config = config
        self.devices: Dict[str, SimpleDevice] = {}
        self.running = False
        self.logger = logging.getLogger(f"{__name__}.{config.config_name}")
        
        # REST API server
        self.rest_server: Optional[RestApiServer] = None
        
        # Data storage for API access
        self.latest_data: Dict[str, Dict[str, DeviceData]] = {}
        
        # Initialize devices
        self._initialize_devices()
    
    def _initialize_devices(self):
        """Initialize devices for each device definition"""
        for device_def in self.config.devices:
            device = SimpleDevice(
                device_id=device_def.device_id,
                device_name=device_def.device_name,
                device_type=device_def.device_type.value,
                data_configs=device_def.data_configs,
                communication=device_def.communication,
                metadata=device_def.metadata.dict()
            )
            self.devices[device_def.device_id] = device
            
            # Initialize data storage
            self.latest_data[device_def.device_id] = {}
            
            self.logger.info(f"Initialized device {device_def.device_name} ({device_def.device_id})")
    
    async def start(self, host: str = "localhost", api_port: int = 8080, enable_api: bool = True):
        """Start the emulator with REST API server"""
        self.running = True
        self.logger.info(f"Starting simple emulator: {self.config.config_name}")
        self.logger.info(f"Managing {len(self.devices)} devices")
        
        # Start REST API server if enabled
        if enable_api:
            self.rest_server = RestApiServer(self, host=host, port=api_port)
            api_task = asyncio.create_task(self.rest_server.start())
            self.logger.info(f"REST API server will start on {host}:{api_port}")
        
        try:
            # Start the main emulation loop
            if enable_api:
                await asyncio.gather(
                    self._main_emulation_loop(),
                    api_task
                )
            else:
                await self._main_emulation_loop()
        except asyncio.CancelledError:
            self.logger.info("Simple emulator stopped")
        except Exception as e:
            self.logger.error(f"Error in simple emulator: {e}")
            raise
    
    async def stop(self):
        """Stop the emulator"""
        self.running = False
        self.logger.info("Stopping simple emulator...")
        
        # Stop REST API server
        if self.rest_server:
            await self.rest_server.stop()
        
        self.logger.info("Simple emulator stopped")
    
    async def _main_emulation_loop(self):
        """Main single-threaded emulation loop for all devices"""
        self.logger.info("Starting main emulation loop")
        
        # Calculate the minimum sleep time based on highest frequency
        min_sleep_time = 0.1  # Default 100ms
        for device in self.devices.values():
            for data_config in device.data_configs:
                if data_config.frequency > 0:
                    sleep_time = 1.0 / data_config.frequency
                    min_sleep_time = min(min_sleep_time, sleep_time)
        
        self.logger.info(f"Using emulation loop frequency: {1.0/min_sleep_time:.1f} Hz")
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Generate data for all devices and all their data types
                for device_id, device in self.devices.items():
                    for data_type_name in device.get_available_data_types():
                        try:
                            # Check if it's time to generate data for this type
                            data_config = next(dc for dc in device.data_configs if dc.name == data_type_name)
                            
                            # Simple time-based generation (can be improved with individual timers)
                            current_time = time.time()
                            if not hasattr(device, '_last_generation_times'):
                                device._last_generation_times = {}
                            
                            last_time = device._last_generation_times.get(data_type_name, 0)
                            generation_interval = 1.0 / data_config.frequency if data_config.frequency > 0 else 1.0
                            
                            if current_time - last_time >= generation_interval:
                                # Generate data
                                device_data = device.generate_device_data(data_type_name)
                                
                                # Store latest data for API access
                                self.latest_data[device_id][data_type_name] = device_data
                                
                                # Log the generated data
                                self.logger.debug(f"Generated {device_id}.{data_type_name}: {device_data.value} {device_data.unit}")
                                
                                # Update last generation time
                                device._last_generation_times[data_type_name] = current_time
                                
                        except Exception as e:
                            self.logger.error(f"Error generating data for {device_id}.{data_type_name}: {e}")
                
                # Calculate sleep time to maintain loop frequency
                loop_duration = time.time() - loop_start
                sleep_time = max(0, min_sleep_time - loop_duration)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
        except asyncio.CancelledError:
            self.logger.info("Main emulation loop stopped")
        except Exception as e:
            self.logger.error(f"Error in main emulation loop: {e}")
            raise
    
    def generate_data_for_device(self, device_id: str, data_type_name: str) -> Optional[DeviceData]:
        """Generate data for a specific device and data type"""
        if device_id not in self.devices:
            self.logger.warning(f"Device {device_id} not found")
            return None
        
        device = self.devices[device_id]
        if data_type_name not in device.get_available_data_types():
            self.logger.warning(f"Data type {data_type_name} not found for device {device_id}")
            return None
        
        try:
            return device.generate_device_data(data_type_name)
        except Exception as e:
            self.logger.error(f"Error generating data for {device_id}.{data_type_name}: {e}")
            return None
    
    def generate_data_for_all_devices(self) -> Dict[str, Dict[str, DeviceData]]:
        """Generate data for all devices and all their data types"""
        all_data = {}
        
        for device_id, device in self.devices.items():
            device_data = {}
            for data_type_name in device.get_available_data_types():
                try:
                    data = device.generate_device_data(data_type_name)
                    device_data[data_type_name] = data
                except Exception as e:
                    self.logger.error(f"Error generating data for {device_id}.{data_type_name}: {e}")
            all_data[device_id] = device_data
        
        return all_data
    
    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific device"""
        if device_id not in self.devices:
            return None
        
        device = self.devices[device_id]
        return {
            "device_id": device.device_id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "data_types": device.get_available_data_types(),
            "current_values": device.get_current_values(),
            "metadata": device.metadata,
            "communication": device.communication
        }
    
    def get_all_devices_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all devices"""
        all_info = {}
        for device_id in self.devices.keys():
            all_info[device_id] = self.get_device_info(device_id)
        return all_info
    
    def get_devices_by_type(self, device_type: str) -> List[str]:
        """Get device IDs by device type"""
        return [device_id for device_id, device in self.devices.items() 
                if device.device_type == device_type]
    
    def get_configuration(self) -> MultiDeviceConfig:
        """Get the current multi-device configuration"""
        return self.config
    
    def get_device(self, device_id: str) -> Optional[SimpleDevice]:
        """Get the device for a specific device ID"""
        return self.devices.get(device_id)
    
    def get_latest_data(self, device_id: str = None, data_type: str = None) -> Dict[str, Any]:
        """Get the latest generated data"""
        if device_id:
            if data_type:
                return self.latest_data.get(device_id, {}).get(data_type)
            else:
                return self.latest_data.get(device_id, {})
        else:
            return self.latest_data
