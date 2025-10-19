"""
Multi-device emulator class
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from shared.models.multi_device_config import MultiDeviceConfig, DeviceDefinition
from shared.models.device_data import DeviceData, DataPoint
from .emulator import DeviceEmulator
from .data_generator import DataGeneratorFactory, BaseDataGenerator
from ..api.rest_server import RestApiServer


class MultiDeviceEmulator:
    """Multi-device emulator that manages multiple devices from a single configuration"""
    
    def __init__(self, config: MultiDeviceConfig):
        self.config = config
        self.device_emulators: Dict[str, DeviceEmulator] = {}
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.logger = logging.getLogger(f"{__name__}.{config.config_name}")
        
        # REST API server
        self.rest_server: Optional[RestApiServer] = None
        
        # Initialize device emulators
        self._initialize_device_emulators()
    
    def _initialize_device_emulators(self):
        """Initialize emulators for each device"""
        for device_def in self.config.devices:
            # Convert DeviceDefinition to DeviceConfig format
            from shared.models.device_config import DeviceConfig
            
            device_config = DeviceConfig(
                device_id=device_def.device_id,
                device_name=device_def.device_name,
                device_type=device_def.device_type.value,
                data_configs=device_def.data_configs,
                communication=device_def.communication,
                metadata=device_def.metadata.dict()
            )
            
            # Create emulator for this device
            emulator = DeviceEmulator(device_config)
            self.device_emulators[device_def.device_id] = emulator
            
            self.logger.info(f"Initialized emulator for {device_def.device_name} ({device_def.device_id})")
    
    async def start(self, host: str = "localhost", base_port: int = 8080, enable_api: bool = True, api_port: int = 8080):
        """Start all device emulators and REST API server"""
        self.running = True
        self.logger.info(f"Starting multi-device emulator: {self.config.config_name}")
        self.logger.info(f"Managing {len(self.device_emulators)} devices")
        
        # Start REST API server if enabled
        if enable_api:
            self.rest_server = RestApiServer(self, host=host, port=api_port)
            api_task = asyncio.create_task(self.rest_server.start())
            self.tasks.append(api_task)
            self.logger.info(f"REST API server will start on {host}:{api_port}")
        
        # Start each device emulator
        for i, (device_id, emulator) in enumerate(self.device_emulators.items()):
            device_def = self.config.get_device_by_id(device_id)
            port = base_port + i + 1  # Start from base_port + 1 to avoid conflict with API
            
            # Override port if specified in device communication config
            if 'port' in device_def.communication:
                port = device_def.communication['port']
            
            task = asyncio.create_task(emulator.start(host=host, port=port))
            self.tasks.append(task)
            
            self.logger.info(f"Started {device_def.device_name} on {host}:{port}")
        
        try:
            # Wait for all tasks
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            self.logger.info("Multi-device emulator stopped")
        except Exception as e:
            self.logger.error(f"Error in multi-device emulator: {e}")
            raise
    
    async def stop(self):
        """Stop all device emulators and REST API server"""
        self.running = False
        self.logger.info("Stopping multi-device emulator...")
        
        # Stop REST API server
        if self.rest_server:
            await self.rest_server.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.logger.info("Multi-device emulator stopped")
    
    async def generate_data_for_device(self, device_id: str, data_type_name: str) -> Optional[DeviceData]:
        """Generate data for a specific device and data type"""
        if device_id not in self.device_emulators:
            self.logger.warning(f"Device {device_id} not found")
            return None
        
        emulator = self.device_emulators[device_id]
        return await emulator.generate_single_data(data_type_name)
    
    async def generate_data_for_all_devices(self) -> Dict[str, Dict[str, DeviceData]]:
        """Generate data for all devices and all their data types"""
        all_data = {}
        
        for device_id, emulator in self.device_emulators.items():
            device_data = {}
            for data_type_name in emulator.get_available_data_types():
                data = await emulator.generate_single_data(data_type_name)
                if data:
                    device_data[data_type_name] = data
            all_data[device_id] = device_data
        
        return all_data
    
    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific device"""
        device_def = self.config.get_device_by_id(device_id)
        if not device_def:
            return None
        
        emulator = self.device_emulators.get(device_id)
        if not emulator:
            return None
        
        return {
            "device_id": device_def.device_id,
            "device_name": device_def.device_name,
            "device_type": device_def.device_type.value,
            "data_types": emulator.get_available_data_types(),
            "current_values": emulator.get_current_values(),
            "metadata": device_def.metadata.dict(),
            "communication": device_def.communication
        }
    
    def get_all_devices_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all devices"""
        all_info = {}
        for device_id in self.device_emulators.keys():
            all_info[device_id] = self.get_device_info(device_id)
        return all_info
    
    def get_devices_by_type(self, device_type: str) -> List[str]:
        """Get device IDs by device type"""
        return [device.device_id for device in self.config.get_devices_by_type(device_type)]
    
    def get_configuration(self) -> MultiDeviceConfig:
        """Get the current multi-device configuration"""
        return self.config
    
    def get_device_emulator(self, device_id: str) -> Optional[DeviceEmulator]:
        """Get the emulator for a specific device"""
        return self.device_emulators.get(device_id)
