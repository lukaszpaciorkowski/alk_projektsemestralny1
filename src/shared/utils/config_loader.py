"""
Configuration loader utilities
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Union
from pydantic import ValidationError

from ..models.device_config import DeviceConfig


class ConfigLoader:
    """Utility class for loading device configurations"""
    
    @staticmethod
    def load_yaml_config(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def load_json_config(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def load_device_config(file_path: Union[str, Path]) -> DeviceConfig:
        """Load and validate device configuration"""
        file_path = Path(file_path)
        
        # Determine file type and load accordingly
        if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
            config_data = ConfigLoader.load_yaml_config(file_path)
        elif file_path.suffix.lower() == '.json':
            config_data = ConfigLoader.load_json_config(file_path)
        else:
            raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
        
        try:
            return DeviceConfig(**config_data)
        except ValidationError as e:
            raise ValueError(f"Invalid configuration: {e}")
    
    # @staticmethod
    # def save_device_config(config: DeviceConfig, file_path: Union[str, Path], format: str = 'yaml'):
    #     """Save device configuration to file"""
    #     file_path = Path(file_path)
        
    #     # Ensure directory exists
    #     file_path.parent.mkdir(parents=True, exist_ok=True)
        
    #     config_dict = config.dict()
        
    #     if format.lower() == 'yaml':
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    #     elif format.lower() == 'json':
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             json.dump(config_dict, f, indent=2, default=str)
    #     else:
    #         raise ValueError(f"Unsupported output format: {format}")
    
    @staticmethod
    def list_config_files(config_dir: Union[str, Path]) -> list[Path]:
        """List all configuration files in a directory"""
        config_dir = Path(config_dir)
        
        if not config_dir.exists():
            return []
        
        config_files = []
        for pattern in ['*.yaml', '*.yml', '*.json']:
            config_files.extend(config_dir.glob(pattern))
        
        return sorted(config_files)
    
    # @staticmethod
    # def create_example_config(device_type: str = "sensor") -> DeviceConfig:
    #     """Create an example device configuration"""
    #     if device_type == "sensor":
    #         return DeviceConfig(
    #             device_id="example_sensor_001",
    #             device_name="Example Sensor",
    #             device_type="sensor",
    #             data_configs=[
    #                 {
    #                     "name": "temperature",
    #                     "data_type": "float",
    #                     "min_value": -40.0,
    #                     "max_value": 85.0,
    #                     "frequency": 1.0,
    #                     "change_step": 0.5,
    #                     "unit": "°C",
    #                     "initial_value": 20.0,
    #                     "noise_level": 0.02,
    #                     "drift_rate": 0.001
    #                 }
    #             ],
    #             communication={"protocol": "tcp", "port": 8080},
    #             metadata={"location": "Example Location"}
    #         )
    #     elif device_type == "actuator":
    #         return DeviceConfig(
    #             device_id="example_actuator_001",
    #             device_name="Example Actuator",
    #             device_type="actuator",
    #             data_configs=[
    #                 {
    #                     "name": "position",
    #                     "data_type": "integer",
    #                     "min_value": 0,
    #                     "max_value": 100,
    #                     "frequency": 2.0,
    #                     "change_step": 5,
    #                     "unit": "%",
    #                     "initial_value": 0,
    #                     "noise_level": 0.01,
    #                     "drift_rate": 0.0
    #                 }
    #             ],
    #             communication={"protocol": "tcp", "port": 8081},
    #             metadata={"location": "Example Location"}
    #         )
    #     else:
    #         raise ValueError(f"Unknown device type: {device_type}")
