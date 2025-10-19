"""
Configuration models for multiple devices
"""

from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from .device_config import DataGenerationConfig, DataType


class DeviceType(str, Enum):
    """Device types"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    CONTROLLER = "controller"
    GATEWAY = "gateway"


class DeviceMetadata(BaseModel):
    """Metadata for individual devices"""
    
    location: str = Field(..., description="Physical location of the device")
    manufacturer: str = Field(..., description="Device manufacturer")
    model: str = Field(..., description="Device model")
    serial_number: Optional[str] = Field(None, description="Device serial number")
    installation_date: Optional[str] = Field(None, description="Installation date")
    maintenance_schedule: Optional[str] = Field(None, description="Maintenance schedule")
    environment: Optional[str] = Field(None, description="Environment conditions")
    notes: Optional[str] = Field(None, description="Additional notes")
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata fields")


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
    
    @validator('data_configs')
    def validate_data_configs(cls, v):
        """Validate that at least one data configuration is provided"""
        if not v:
            raise ValueError('At least one data configuration must be provided')
        return v


class MultiDeviceConfig(BaseModel):
    """Configuration for multiple devices"""
    
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
    
    @validator('devices')
    def validate_devices(cls, v):
        """Validate that at least one device is provided"""
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
