"""
Simplified configuration models for device emulation
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator
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
    
    @field_validator('min_value', 'max_value')
    @classmethod
    def validate_range(cls, v, info):
        """Validate that min_value <= max_value"""
        if info.data and 'min_value' in info.data and 'max_value' in info.data:
            if info.data['min_value'] > info.data['max_value']:
                raise ValueError('min_value must be less than or equal to max_value')
        return v
    
    @field_validator('initial_value')
    @classmethod
    def validate_initial_value(cls, v, info):
        """Validate initial value is within range"""
        if v is not None and info.data and 'min_value' in info.data and 'max_value' in info.data:
            if not (info.data['min_value'] <= v <= info.data['max_value']):
                raise ValueError('initial_value must be within min_value and max_value range')
        return v


class DeviceType(str, Enum):
    """Device types"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    CONTROLLER = "controller"
    GATEWAY = "gateway"


class DeviceMetadata(BaseModel):
    """Simplified metadata for devices"""
    
    location: str = Field(..., description="Physical location of the device")
    manufacturer: str = Field(..., description="Device manufacturer")
    model: str = Field(..., description="Device model")
    serial_number: Optional[str] = Field(None, description="Device serial number")
    installation_date: Optional[str] = Field(None, description="Installation date")
    environment: Optional[str] = Field(None, description="Environment conditions")
    notes: Optional[str] = Field(None, description="Additional notes")


class DeviceDefinition(BaseModel):
    """Definition for a single device"""
    
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    device_type: DeviceType = Field(..., description="Type of device")
    data_configs: List[DataGenerationConfig] = Field(
        ..., 
        description="List of data generation configurations"
    )
    communication: Dict[str, Any] = Field(
        default_factory=dict,
        description="Communication settings for this device"
    )
    metadata: DeviceMetadata = Field(..., description="Device metadata")
    
    @field_validator('data_configs')
    @classmethod
    def validate_data_configs(cls, v):
        """Validate that at least one data configuration is provided"""
        if not v:
            raise ValueError('At least one data configuration must be provided')
        return v


class DeviceConfig(BaseModel):
    """Simplified configuration for multiple devices"""
    
    config_name: str = Field(..., description="Name of this configuration")
    config_version: str = Field(default="1.0", description="Configuration version")
    description: Optional[str] = Field(None, description="Configuration description")
    
    # Global settings
    global_communication: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global communication settings"
    )
    global_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global metadata applied to all devices"
    )
    
    # Device definitions
    devices: List[DeviceDefinition] = Field(
        ..., 
        description="List of device definitions"
    )
    
    # Configuration metadata
    created_by: Optional[str] = Field(None, description="Configuration creator")
    created_date: Optional[str] = Field(None, description="Creation date")
    tags: List[str] = Field(default_factory=list, description="Configuration tags")
    
    @field_validator('devices')
    @classmethod
    def validate_devices(cls, v):
        """Validate that at least one device is provided and device IDs are unique"""
        if not v:
            raise ValueError('At least one device must be provided')
        
        # Check for unique device IDs
        device_ids = [device.device_id for device in v]
        if len(device_ids) != len(set(device_ids)):
            raise ValueError('Device IDs must be unique')
        
        return v
    
    def get_device_by_id(self, device_id: str) -> Optional[DeviceDefinition]:
        """Get device definition by ID"""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None
    
    def get_devices_by_type(self, device_type: DeviceType) -> List[DeviceDefinition]:
        """Get all devices of a specific type"""
        return [device for device in self.devices if device.device_type == device_type]
    
    def get_all_device_ids(self) -> List[str]:
        """Get all device IDs"""
        return [device.device_id for device in self.devices]


# Alias for backward compatibility
MultiDeviceConfig = DeviceConfig
