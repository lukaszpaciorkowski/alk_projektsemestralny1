"""
Configuration loader utilities
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Union
from pydantic import ValidationError

from ..models.device_config import DeviceConfig
from ..models.multi_device_config import MultiDeviceConfig


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
    
    @staticmethod
    def load_multi_device_config(file_path: Union[str, Path]) -> MultiDeviceConfig:
        """Load and validate multi-device configuration"""
        file_path = Path(file_path)
        
        # Determine file type and load accordingly
        if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
            config_data = ConfigLoader.load_yaml_config(file_path)
        elif file_path.suffix.lower() == '.json':
            config_data = ConfigLoader.load_json_config(file_path)
        else:
            raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
        
        try:
            return MultiDeviceConfig(**config_data)
        except ValidationError as e:
            raise ValueError(f"Invalid multi-device configuration: {e}")

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
        