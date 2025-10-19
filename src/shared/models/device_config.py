"""
Configuration models for device emulation
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DataType(str, Enum):
    """Supported data types"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"


class DataGenerationConfig(BaseModel):
    """Configuration for generating a specific type of data"""
    
    name: str = Field(..., description="Name of the data type (e.g., temperature)")
    data_type: DataType = Field(..., description="Type of data to generate")
    min_value: Union[int, float] = Field(..., description="Minimum value")
    max_value: Union[int, float] = Field(..., description="Maximum value")
    frequency: float = Field(..., description="Frequency in Hz (data points per second)")
    change_step: Union[int, float] = Field(..., description="Maximum change per time step")
    unit: str = Field(default="", description="Unit of measurement")
    initial_value: Optional[Union[int, float, str, bool]] = Field(
        default=None, 
        description="Initial value (if not provided, will be random within range)"
    )
    noise_level: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Noise level (0.0 = no noise, 1.0 = maximum noise)"
    )
    drift_rate: float = Field(
        default=0.0, 
        description="Drift rate (change per second)"
    )
    custom_params: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Custom parameters for specific data types"
    )
    
    @validator('min_value', 'max_value')
    def validate_range(cls, v, values):
        """Validate that min_value <= max_value"""
        if 'min_value' in values and 'max_value' in values:
            if values['min_value'] > values['max_value']:
                raise ValueError('min_value must be less than or equal to max_value')
        return v
    
    @validator('initial_value')
    def validate_initial_value(cls, v, values):
        """Validate initial value is within range"""
        if v is not None and 'min_value' in values and 'max_value' in values:
            if not (values['min_value'] <= v <= values['max_value']):
                raise ValueError('initial_value must be within min_value and max_value range')
        return v


class DeviceConfig(BaseModel):
    """Configuration for a device emulator"""
    
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    device_type: str = Field(..., description="Type of device (e.g., sensor, actuator)")
    data_configs: List[DataGenerationConfig] = Field(
        ..., 
        description="List of data generation configurations"
    )
    communication: Dict[str, Any] = Field(
        default_factory=dict,
        description="Communication settings"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional device metadata"
    )
    
    @validator('data_configs')
    def validate_data_configs(cls, v):
        """Validate that at least one data configuration is provided"""
        if not v:
            raise ValueError('At least one data configuration must be provided')
        return v
