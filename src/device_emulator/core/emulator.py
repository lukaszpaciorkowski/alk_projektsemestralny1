"""
Main device emulator class
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from shared.models.device_config import DeviceConfig, DataGenerationConfig
from shared.models.device_data import DeviceData, DataPoint
from .data_generator import DataGeneratorFactory, BaseDataGenerator


class DeviceEmulator:
    """Main device emulator class that generates data based on configuration"""
    
    def __init__(self, config: DeviceConfig):
        self.config = config
        self.generators: Dict[str, BaseDataGenerator] = {}
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.logger = logging.getLogger(f"{__name__}.{config.device_id}")
        
        # Initialize data generators
        self._initialize_generators()
    
    def _initialize_generators(self):
        """Initialize data generators for each configured data type"""
        for data_config in self.config.data_configs:
            generator = DataGeneratorFactory.create_generator(data_config)
            self.generators[data_config.name] = generator
            self.logger.info(f"Initialized generator for {data_config.name} ({data_config.data_type})")
    
    async def start(self, host: str = "localhost", port: int = 8080):
        """Start the device emulator"""
        self.running = True
        self.logger.info(f"Starting device emulator: {self.config.device_name} ({self.config.device_id})")
        
        # Start data generation tasks for each configured data type
        for name, generator in self.generators.items():
            data_config = next(dc for dc in self.config.data_configs if dc.name == name)
            task = asyncio.create_task(self._data_generation_loop(name, generator, data_config))
            self.tasks.append(task)
        
        # Start communication server (placeholder for now)
        server_task = asyncio.create_task(self._start_communication_server(host, port))
        self.tasks.append(server_task)
        
        try:
            # Wait for all tasks
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            self.logger.info("Device emulator stopped")
        except Exception as e:
            self.logger.error(f"Error in device emulator: {e}")
            raise
    
    async def stop(self):
        """Stop the device emulator"""
        self.running = False
        self.logger.info("Stopping device emulator...")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.logger.info("Device emulator stopped")
    
    async def _data_generation_loop(self, name: str, generator: BaseDataGenerator, config: DataGenerationConfig):
        """Data generation loop for a specific data type"""
        self.logger.info(f"Starting data generation for {name} at {config.frequency} Hz")
        
        try:
            while self.running:
                # Generate data point
                data_point = await generator.generate_data_point()
                
                # Create device data
                device_data = DeviceData(
                    device_id=self.config.device_id,
                    timestamp=data_point.timestamp,
                    data_type=name,
                    value=data_point.value,
                    unit=config.unit,
                    metadata={
                        "data_type": config.data_type.value,
                        "frequency": config.frequency,
                        "noise_level": config.noise_level,
                        "drift_rate": config.drift_rate
                    }
                )
                
                # Log the generated data
                self.logger.debug(f"Generated {name}: {data_point.value} {config.unit}")
                
                # Here you would typically send the data to clients
                # For now, we'll just store it or send it via the communication server
                await self._handle_generated_data(device_data)
                
                # Wait for next generation based on frequency
                if config.frequency > 0:
                    await asyncio.sleep(1.0 / config.frequency)
                else:
                    await asyncio.sleep(1.0)  # Default to 1 Hz if frequency is 0
                    
        except asyncio.CancelledError:
            self.logger.info(f"Data generation stopped for {name}")
        except Exception as e:
            self.logger.error(f"Error in data generation for {name}: {e}")
            raise
    
    async def _handle_generated_data(self, device_data: DeviceData):
        """Handle generated data (placeholder for communication)"""
        # This is where you would implement the actual communication
        # For now, we'll just log it or store it
        pass
    
    async def _start_communication_server(self, host: str, port: int):
        """Start communication server (placeholder)"""
        self.logger.info(f"Starting communication server on {host}:{port}")
        
        try:
            while self.running:
                # Placeholder for communication server implementation
                # This could be TCP, WebSocket, MQTT, etc.
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            self.logger.info("Communication server stopped")
    
    async def generate_single_data(self, data_type_name: str) -> Optional[DeviceData]:
        """Generate a single data point for a specific data type"""
        if data_type_name not in self.generators:
            self.logger.warning(f"Data type {data_type_name} not found")
            return None
        
        generator = self.generators[data_type_name]
        data_config = next(dc for dc in self.config.data_configs if dc.name == data_type_name)
        
        data_point = await generator.generate_data_point()
        
        return DeviceData(
            device_id=self.config.device_id,
            timestamp=data_point.timestamp,
            data_type=data_type_name,
            value=data_point.value,
            unit=data_config.unit,
            metadata={
                "data_type": data_config.data_type.value,
                "frequency": data_config.frequency,
                "noise_level": data_config.noise_level,
                "drift_rate": data_config.drift_rate
            }
        )
    
    def get_configuration(self) -> DeviceConfig:
        """Get the current device configuration"""
        return self.config
    
    def get_available_data_types(self) -> List[str]:
        """Get list of available data types"""
        return list(self.generators.keys())
    
    def get_current_values(self) -> Dict[str, Any]:
        """Get current values for all data types"""
        current_values = {}
        for name, generator in self.generators.items():
            current_values[name] = generator.current_value
        return current_values
