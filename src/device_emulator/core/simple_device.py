"""
Simplified device class without ABC
"""

import random
import math
import logging
from typing import Union, Any, Dict, List
from datetime import datetime, timedelta

from shared.models.config import DataGenerationConfig, DataType
from shared.models.device_data import DeviceData, DataPoint


class SimpleDevice:
    """Simplified device class that handles all data types without ABC"""
    
    def __init__(self, device_id: str, device_name: str, device_type: str, 
                 data_configs: List[DataGenerationConfig], 
                 communication: Dict[str, Any] = None, 
                 metadata: Dict[str, Any] = None):
        self.device_id = device_id
        self.device_name = device_name
        self.device_type = device_type
        self.data_configs = data_configs
        self.communication = communication or {}
        self.metadata = metadata or {}
        
        self.logger = logging.getLogger(f"{__name__}.{device_id}")
        
        # Initialize data generators for each configured data type
        self.generators: Dict[str, Dict[str, Any]] = {}
        self._initialize_generators()
    
    def _initialize_generators(self):
        """Initialize data generators for each configured data type"""
        for data_config in self.data_configs:
            generator = {
                'config': data_config,
                'current_value': self._get_initial_value(data_config),
                'last_update': datetime.now(),
                'drift_offset': 0.0
            }
            self.generators[data_config.name] = generator
            self.logger.info(f"Initialized generator for {data_config.name} ({data_config.data_type})")
    
    def _get_initial_value(self, config: DataGenerationConfig) -> Union[int, float, str, bool]:
        """Get initial value for the data generator"""
        if config.initial_value is not None:
            return config.initial_value
        
        if config.data_type == DataType.INTEGER:
            return random.randint(int(config.min_value), int(config.max_value))
        elif config.data_type == DataType.FLOAT:
            return random.uniform(config.min_value, config.max_value)
        elif config.data_type == DataType.BOOLEAN:
            return random.choice([True, False])
        elif config.data_type == DataType.STRING:
            # For strings, use possible_states if available, otherwise generate random
            if 'possible_states' in config.custom_params:
                return random.choice(config.custom_params['possible_states'])
            return self._generate_random_string(config)
        else:
            raise ValueError(f"Unsupported data type: {config.data_type}")
    
    def _generate_random_string(self, config: DataGenerationConfig) -> str:
        """Generate a random string value"""
        length = config.custom_params.get('string_length', 10)
        chars = config.custom_params.get('string_chars', 'abcdefghijklmnopqrstuvwxyz0123456789')
        return ''.join(random.choices(chars, k=length))
    
    def _apply_noise(self, value: Union[int, float], config: DataGenerationConfig) -> Union[int, float]:
        """Apply noise to the value"""
        if config.noise_level == 0.0:
            return value
        
        if config.data_type == DataType.INTEGER:
            noise_range = (config.max_value - config.min_value) * config.noise_level
            noise = random.uniform(-noise_range, noise_range)
            return int(value + noise)
        else:  # FLOAT
            noise_range = (config.max_value - config.min_value) * config.noise_level
            noise = random.uniform(-noise_range, noise_range)
            return value + noise
    
    def _apply_drift(self, value: Union[int, float], time_delta: timedelta, 
                    config: DataGenerationConfig, generator: Dict[str, Any]) -> Union[int, float]:
        """Apply drift to the value based on time elapsed"""
        if config.drift_rate == 0.0:
            return value
        
        # Calculate drift based on time elapsed
        drift = config.drift_rate * time_delta.total_seconds()
        generator['drift_offset'] += drift
        
        if config.data_type == DataType.INTEGER:
            return int(value + generator['drift_offset'])
        else:  # FLOAT
            return value + generator['drift_offset']
    
    def _clamp_value(self, value: Union[int, float], config: DataGenerationConfig) -> Union[int, float]:
        """Clamp value to the configured range"""
        if config.data_type == DataType.INTEGER:
            return max(int(config.min_value), min(int(config.max_value), int(value)))
        else:  # FLOAT
            return max(config.min_value, min(config.max_value, value))
    
    def _generate_next_value(self, name: str) -> Union[int, float, str, bool]:
        """Generate the next value based on the configuration"""
        generator = self.generators[name]
        config = generator['config']
        now = datetime.now()
        time_delta = now - generator['last_update']
        
        if config.data_type == DataType.INTEGER:
            # Calculate maximum change based on time elapsed since last update
            max_change = config.change_step * time_delta.total_seconds()
            change = random.uniform(-max_change, max_change)
            new_value = generator['current_value'] + change
            new_value = self._clamp_value(new_value, config)
            generator['current_value'] = new_value
            return int(new_value)
            
        elif config.data_type == DataType.FLOAT:
            # Calculate maximum change based on time elapsed since last update
            max_change = config.change_step * time_delta.total_seconds()
            change = random.uniform(-max_change, max_change)
            new_value = generator['current_value'] + change
            new_value = self._clamp_value(new_value, config)
            generator['current_value'] = new_value
            return float(new_value)
            
        elif config.data_type == DataType.BOOLEAN:
            # For boolean, we can either keep the same value or flip it
            flip_probability = min(1.0, config.change_step * time_delta.total_seconds())
            if random.random() < flip_probability:
                generator['current_value'] = not generator['current_value']
            return bool(generator['current_value'])
            
        elif config.data_type == DataType.STRING:
            # For strings, we can either keep the same or generate a new one
            change_probability = min(1.0, config.change_step * time_delta.total_seconds())
            if random.random() < change_probability:
                if 'possible_states' in config.custom_params:
                    generator['current_value'] = random.choice(config.custom_params['possible_states'])
                else:
                    generator['current_value'] = self._generate_random_string(config)
            return str(generator['current_value'])
        
        else:
            raise ValueError(f"Unsupported data type: {config.data_type}")
    
    def generate_data_point(self, name: str) -> DataPoint:
        """Generate a data point with timestamp and value"""
        if name not in self.generators:
            raise ValueError(f"Data type {name} not found")
        
        generator = self.generators[name]
        config = generator['config']
        now = datetime.now()
        time_delta = now - generator['last_update']
        
        # Generate next value
        value = self._generate_next_value(name)
        
        # Apply noise and drift for numeric types
        if config.data_type in [DataType.INTEGER, DataType.FLOAT]:
            value = self._apply_drift(value, time_delta, config, generator)
            value = self._apply_noise(value, config)
            value = self._clamp_value(value, config)
        
        generator['last_update'] = now
        return DataPoint(timestamp=now, value=value)
    
    def generate_device_data(self, name: str) -> DeviceData:
        """Generate device data for a specific data type"""
        if name not in self.generators:
            raise ValueError(f"Data type {name} not found")
        
        config = self.generators[name]['config']
        data_point = self.generate_data_point(name)
        
        return DeviceData(
            device_id=self.device_id,
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
    
    def get_available_data_types(self) -> List[str]:
        """Get list of available data types"""
        return list(self.generators.keys())
    
    def get_current_values(self) -> Dict[str, Any]:
        """Get current values for all data types"""
        current_values = {}
        for name, generator in self.generators.items():
            current_values[name] = generator['current_value']
        return current_values
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get the current device configuration"""
        return {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'data_configs': [gen['config'] for gen in self.generators.values()],
            'communication': self.communication,
            'metadata': self.metadata
        }
