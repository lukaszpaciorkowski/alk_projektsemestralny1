"""
Data models for device-generated data
"""

from datetime import datetime
from typing import Any, Dict, Union
from pydantic import BaseModel, Field


class DeviceData(BaseModel):
    """Model for device-generated data"""
    
    device_id: str = Field(..., description="Unique device identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")
    data_type: str = Field(..., description="Type of data (e.g., temperature, pressure)")
    value: Union[int, float, str, bool] = Field(..., description="The actual data value")
    unit: str = Field(default="", description="Unit of measurement")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataPoint(BaseModel):
    """Single data point with timestamp and value"""
    
    timestamp: datetime = Field(default_factory=datetime.now)
    value: Union[int, float, str, bool]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
