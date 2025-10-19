# Device Emulator

The Device Emulator is a flexible Python-based system for generating realistic device data based on configurable parameters. It supports multiple data types, realistic noise and drift simulation, and various communication protocols.

## Features

- **Multiple Data Types**: Support for integer, float, boolean, and string data
- **Configurable Parameters**: 
  - Data type and range (min/max values)
  - Generation frequency (Hz)
  - Change step (maximum change per time period)
  - Noise level and drift rate
  - Initial values and units
- **Realistic Simulation**: Includes noise, drift, and controlled value changes
- **YAML/JSON Configuration**: Easy-to-use configuration files
- **Extensible Architecture**: Easy to add new data types and generators

## Quick Start

### 1. Create a Configuration

Create a YAML configuration file in `config/device_configs/`:

```yaml
device_id: "my_sensor_001"
device_name: "My Temperature Sensor"
device_type: "sensor"
data_configs:
  - name: "temperature"
    data_type: "float"
    min_value: -40.0
    max_value: 85.0
    frequency: 1.0  # 1 Hz
    change_step: 0.5  # Max 0.5°C change per second
    unit: "°C"
    initial_value: 20.0
    noise_level: 0.02  # 2% noise
    drift_rate: 0.001  # 0.001°C per second drift
communication:
  protocol: "tcp"
  port: 8080
```

### 2. Run the Emulator

```bash
# Using configuration file
python -m device_emulator.main --config config/device_configs/my_sensor.yaml

# Using default configuration
python -m device_emulator.main

# With verbose output
python -m device_emulator.main --config my_config.yaml --verbose
```

### 3. Create Example Configurations

```bash
# Create example sensor configuration
python -m device_emulator.main --create-example sensor

# Create example actuator configuration
python -m device_emulator.main --create-example actuator

# List available configurations
python -m device_emulator.main --list-configs
```

## Configuration Parameters

### Data Generation Configuration

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `name` | string | Name of the data type | "temperature" |
| `data_type` | enum | Type of data to generate | "float", "integer", "boolean", "string" |
| `min_value` | number | Minimum value | -40.0 |
| `max_value` | number | Maximum value | 85.0 |
| `frequency` | float | Generation frequency in Hz | 1.0 |
| `change_step` | number | Max change per time step | 0.5 |
| `unit` | string | Unit of measurement | "°C" |
| `initial_value` | any | Initial value (optional) | 20.0 |
| `noise_level` | float | Noise level (0.0-1.0) | 0.02 |
| `drift_rate` | float | Drift rate per second | 0.001 |

### Data Types

#### Float
- Continuous numeric values
- Supports noise and drift
- Example: temperature, pressure, voltage

#### Integer
- Discrete numeric values
- Supports noise and drift
- Example: RPM, count, position

#### Boolean
- True/false values
- Change probability based on change_step
- Example: status, alarm, switch

#### String
- Text values
- Configurable character set and length
- Example: status messages, IDs

## Example Configurations

### Temperature Sensor
```yaml
device_id: "temp_sensor_001"
device_name: "Temperature Sensor"
device_type: "sensor"
data_configs:
  - name: "temperature"
    data_type: "float"
    min_value: -40.0
    max_value: 85.0
    frequency: 1.0
    change_step: 0.5
    unit: "°C"
    initial_value: 20.0
    noise_level: 0.02
    drift_rate: 0.001
```

### Motor Controller
```yaml
device_id: "motor_001"
device_name: "Motor Controller"
device_type: "actuator"
data_configs:
  - name: "rpm"
    data_type: "integer"
    min_value: 0
    max_value: 3000
    frequency: 10.0
    change_step: 50
    unit: "RPM"
    initial_value: 0
    noise_level: 0.01
  - name: "status"
    data_type: "string"
    min_value: 0
    max_value: 1
    frequency: 0.2
    change_step: 0.05
    unit: ""
    initial_value: "idle"
    custom_params:
      possible_states: ["idle", "running", "error"]
```

## Programmatic Usage

```python
from shared.models.device_config import DeviceConfig, DataGenerationConfig, DataType
from device_emulator.core.emulator import DeviceEmulator

# Create configuration
config = DeviceConfig(
    device_id="my_device",
    device_name="My Device",
    device_type="sensor",
    data_configs=[
        DataGenerationConfig(
            name="temperature",
            data_type=DataType.FLOAT,
            min_value=20.0,
            max_value=30.0,
            frequency=1.0,
            change_step=0.2,
            unit="°C"
        )
    ]
)

# Create and run emulator
emulator = DeviceEmulator(config)
await emulator.start()
```

## Command Line Options

```bash
python -m device_emulator.main [OPTIONS]

Options:
  --config, -c PATH     Path to device configuration file
  --device-id ID        Device ID (overrides config)
  --host HOST           Host to bind to (default: localhost)
  --port PORT           Port to bind to (overrides config)
  --verbose, -v         Verbose output
  --list-configs        List available configuration files
  --create-example TYPE Create example configuration (sensor/actuator)
```

## Architecture

The device emulator consists of several key components:

- **DeviceConfig**: Configuration model with validation
- **DataGenerationConfig**: Individual data type configuration
- **BaseDataGenerator**: Abstract base class for data generators
- **Specific Generators**: IntegerDataGenerator, FloatDataGenerator, etc.
- **DeviceEmulator**: Main emulator class that coordinates data generation
- **ConfigLoader**: Utility for loading/saving configurations

## Extending the Emulator

### Adding New Data Types

1. Create a new generator class inheriting from `BaseDataGenerator`
2. Implement the `generate_next_value()` method
3. Add the new data type to the `DataType` enum
4. Update the `DataGeneratorFactory`

### Adding New Communication Protocols

1. Extend the `DeviceEmulator._start_communication_server()` method
2. Implement protocol-specific communication logic
3. Update configuration schema to support new protocol parameters

## Examples

See the `examples/` directory for complete working examples:

- `basic_emulator.py`: Simple programmatic example
- `config_based_emulator.py`: Configuration file-based example

## Troubleshooting

### Common Issues

1. **Configuration not found**: Ensure the config file path is correct
2. **Invalid configuration**: Check YAML syntax and required fields
3. **Import errors**: Make sure the src directory is in Python path

### Debug Mode

Use `--verbose` flag for detailed logging:

```bash
python -m device_emulator.main --config my_config.yaml --verbose
```
