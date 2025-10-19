"""
Data generators for different data types
"""

import random
import math
import asyncio
from abc import ABC, abstractmethod
from typing import Union, Any, Dict
from datetime import datetime, timedelta

from shared.models.device_config import DataGenerationConfig, DataType
from shared.models.device_data import DeviceData, DataPoint


class BaseDataGenerator(ABC):
    """Base class for data generators"""
    
    def __init__(self, config: DataGenerationConfig):
        self.config = config
        self.current_value = self._get_initial_value()
        self.last_update = datetime.now()
        self.drift_offset = 0.0
        
    def _get_initial_value(self) -> Union[int, float, str, bool]:
        """Get initial value for the data generator"""
        if self.config.initial_value is not None:
            return self.config.initial_value
        
        if self.config.data_type == DataType.INTEGER:
            return random.randint(int(self.config.min_value), int(self.config.max_value))
        elif self.config.data_type == DataType.FLOAT:
            return random.uniform(self.config.min_value, self.config.max_value)
        elif self.config.data_type == DataType.BOOLEAN:
            return random.choice([True, False])
        elif self.config.data_type == DataType.STRING:
            # For strings, use possible_states if available, otherwise generate random
            if 'possible_states' in self.config.custom_params:
                return random.choice(self.config.custom_params['possible_states'])
            return self._generate_random_string()
        else:
            raise ValueError(f"Unsupported data type: {self.config.data_type}")
    
    def _generate_random_string(self) -> str:
        """Generate a random string value"""
        # Simple string generation - can be customized based on custom_params
        length = self.config.custom_params.get('string_length', 10)
        chars = self.config.custom_params.get('string_chars', 'abcdefghijklmnopqrstuvwxyz0123456789')
        return ''.join(random.choices(chars, k=length))
    
    def _apply_noise(self, value: Union[int, float]) -> Union[int, float]:
        """Apply noise to the value"""
        if self.config.noise_level == 0.0:
            return value
        
        if self.config.data_type == DataType.INTEGER:
            noise_range = (self.config.max_value - self.config.min_value) * self.config.noise_level
            noise = random.uniform(-noise_range, noise_range)
            return int(value + noise)
        else:  # FLOAT
            noise_range = (self.config.max_value - self.config.min_value) * self.config.noise_level
            noise = random.uniform(-noise_range, noise_range)
            return value + noise
    
    def _apply_drift(self, value: Union[int, float], time_delta: timedelta) -> Union[int, float]:
        """Apply drift to the value based on time elapsed"""
        if self.config.drift_rate == 0.0:
            return value
        
        # Calculate drift based on time elapsed
        drift = self.config.drift_rate * time_delta.total_seconds()
        self.drift_offset += drift
        
        if self.config.data_type == DataType.INTEGER:
            return int(value + self.drift_offset)
        else:  # FLOAT
            return value + self.drift_offset
    
    def _clamp_value(self, value: Union[int, float]) -> Union[int, float]:
        """Clamp value to the configured range"""
        if self.config.data_type == DataType.INTEGER:
            return max(int(self.config.min_value), min(int(self.config.max_value), int(value)))
        else:  # FLOAT
            return max(self.config.min_value, min(self.config.max_value, value))
    
    @abstractmethod
    async def generate_next_value(self) -> Union[int, float, str, bool]:
        """Generate the next value based on the configuration"""
        pass
    
    async def generate_data_point(self) -> DataPoint:
        """Generate a data point with timestamp and value"""
        now = datetime.now()
        time_delta = now - self.last_update
        
        # Generate next value
        value = await self.generate_next_value()
        
        # Apply noise and drift for numeric types
        if self.config.data_type in [DataType.INTEGER, DataType.FLOAT]:
            value = self._apply_drift(value, time_delta)
            value = self._apply_noise(value)
            value = self._clamp_value(value)
        
        self.last_update = now
        return DataPoint(timestamp=now, value=value)


class IntegerDataGenerator(BaseDataGenerator):
    """Generator for integer data"""
    
    async def generate_next_value(self) -> int:
        """Generate next integer value with controlled change"""
        # Calculate maximum change based on time elapsed since last update
        now = datetime.now()
        time_delta = now - self.last_update
        max_change = self.config.change_step * time_delta.total_seconds()
        
        # Generate random change within the step limit
        change = random.uniform(-max_change, max_change)
        new_value = self.current_value + change
        
        # Clamp to range
        new_value = self._clamp_value(new_value)
        
        # Update current value
        self.current_value = new_value
        return int(new_value)


class FloatDataGenerator(BaseDataGenerator):
    """Generator for float data"""
    
    async def generate_next_value(self) -> float:
        """Generate next float value with controlled change"""
        # Calculate maximum change based on time elapsed since last update
        now = datetime.now()
        time_delta = now - self.last_update
        max_change = self.config.change_step * time_delta.total_seconds()
        
        # Generate random change within the step limit
        change = random.uniform(-max_change, max_change)
        new_value = self.current_value + change
        
        # Clamp to range
        new_value = self._clamp_value(new_value)
        
        # Update current value
        self.current_value = new_value
        return float(new_value)


class BooleanDataGenerator(BaseDataGenerator):
    """Generator for boolean data"""
    
    async def generate_next_value(self) -> bool:
        """Generate next boolean value"""
        # For boolean, we can either keep the same value or flip it
        # Use a probability based on change_step (interpreted as flip probability per second)
        now = datetime.now()
        time_delta = now - self.last_update
        
        # Calculate flip probability
        flip_probability = min(1.0, self.config.change_step * time_delta.total_seconds())
        
        if random.random() < flip_probability:
            self.current_value = not self.current_value
        
        return bool(self.current_value)


class StringDataGenerator(BaseDataGenerator):
    """Generator for string data"""
    
    async def generate_next_value(self) -> str:
        """Generate next string value"""
        # For strings, we can either keep the same or generate a new one
        # Use change_step as the probability of generating a new string per second
        now = datetime.now()
        time_delta = now - self.last_update
        
        change_probability = min(1.0, self.config.change_step * time_delta.total_seconds())
        
        if random.random() < change_probability:
            # Use possible_states if available, otherwise generate random string
            if 'possible_states' in self.config.custom_params:
                self.current_value = random.choice(self.config.custom_params['possible_states'])
            else:
                self.current_value = self._generate_random_string()
        
        return str(self.current_value)


class DataGeneratorFactory:
    """Factory for creating data generators based on configuration"""
    
    @staticmethod
    def create_generator(config: DataGenerationConfig) -> BaseDataGenerator:
        """Create a data generator based on the configuration"""
        if config.data_type == DataType.INTEGER:
            return IntegerDataGenerator(config)
        elif config.data_type == DataType.FLOAT:
            return FloatDataGenerator(config)
        elif config.data_type == DataType.BOOLEAN:
            return BooleanDataGenerator(config)
        elif config.data_type == DataType.STRING:
            return StringDataGenerator(config)
        else:
            raise ValueError(f"Unsupported data type: {config.data_type}")
