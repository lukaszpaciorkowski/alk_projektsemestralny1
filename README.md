# Device Emulator System

A comprehensive system for emulating IoT devices, managing data streams, and visualizing device data through a REST API and Qt-based graphical interface.

## Table of Contents

1. [Device Emulator and Configuration](#1-device-emulator-and-configuration)
2. [Data Manager and REST Server](#2-data-manager-and-rest-server)
3. [API Client](#3-api-client)

---

## 1. Device Emulator and Configuration

### Overview

The device emulator system simulates IoT devices that generate data according to configurable parameters. It supports multiple device types (sensors, actuators, controllers, gateways) and various data types (integer, float, string, boolean).

### Components

#### 1.1 Configuration Files

Configuration files are written in YAML format and define:
- **Device definitions**: Device ID, name, type, and metadata
- **Data generation configs**: For each data type a device can generate
- **Global settings**: Communication parameters and metadata applied to all devices

**Configuration Structure:**
```yaml
config_name: "Industrial Plant Monitoring System"
config_version: "1.0"
description: "Complete configuration for industrial plant"

devices:
  - device_id: "temp_sensor_001"
    device_name: "Temperature Sensor - Room A"
    device_type: "sensor"
    data_configs:
      - name: "temperature"
        data_type: "float"
        min_value: -40.0
        max_value: 85.0
        frequency: 1.0  # Hz (data points per second)
        change_step: 0.5
        unit: "°C"
        initial_value: 20.0
        noise_level: 0.02
        drift_rate: 0.001
```

**Key Configuration Parameters:**
- `frequency`: Data generation rate in Hz (points per second)
- `min_value` / `max_value`: Value range constraints
- `change_step`: Maximum change per time step
- `noise_level`: Random noise level (0.0 to 1.0)
- `drift_rate`: Gradual value drift over time
- `initial_value`: Starting value (optional, random if not specified)

#### 1.2 Configuration Loader (`ConfigLoader`)

The `ConfigLoader` class (`src/shared/utils/config_loader.py`) handles loading and validating configuration files:

**Features:**
- Supports YAML and JSON formats
- Validates configuration using Pydantic models
- Provides error messages for invalid configurations
- Can list all configuration files in a directory

**Usage:**
```python
from shared.utils.config_loader import ConfigLoader

config_loader = ConfigLoader()
config = config_loader.load_multi_device_config("config/unified_device_config.yaml")
```

**Validation:**
- Ensures `min_value <= max_value`
- Validates `initial_value` is within range
- Checks required fields are present
- Validates data types and constraints

#### 1.3 Configuration Models (`src/shared/models/config.py`)

Pydantic models define the configuration structure:

- **`DeviceConfig`**: Top-level configuration container
- **`DeviceDefinition`**: Individual device configuration
- **`DataGenerationConfig`**: Data type generation parameters
- **`DeviceType`**: Enum for device types (sensor, actuator, controller, gateway)
- **`DataType`**: Enum for data types (integer, float, string, boolean)
- **`DeviceMetadata`**: Device metadata (location, manufacturer, model, etc.)

#### 1.4 Simple Device (`SimpleDevice`)

The `SimpleDevice` class (`src/device_emulator/core/simple_device.py`) represents a single device:

**Features:**
- Generates data for multiple data types simultaneously
- Supports realistic data generation with:
  - **Noise**: Random variations in values
  - **Drift**: Gradual long-term changes
  - **Change constraints**: Limits on how fast values can change
- Maintains state for each data type independently
- Generates `DeviceData` objects with timestamps

**Data Generation Process:**
1. Checks if enough time has passed since last generation (based on frequency)
2. Calculates new value considering:
   - Previous value
   - Time delta since last update
   - Change step constraints
   - Drift rate
3. Applies noise
4. Clamps value to min/max range
5. Returns `DeviceData` object with timestamp

#### 1.5 Simple Emulator (`SimpleEmulator`)

The `SimpleEmulator` class (`src/device_emulator/core/simple_emulator.py`) manages multiple devices:

**Features:**
- Single-threaded emulation loop for all devices
- Manages device lifecycle (initialization, data generation, shutdown)
- Integrates with REST API server
- Supports instant data generation for CSV export

**Main Loop:**
- Calculates minimum sleep time based on highest frequency device
- Iterates through all devices and their data types
- Generates data when appropriate time intervals have passed
- Stores latest data for API access

**CSV Generation Mode:**
- Can generate data instantly for a specified duration
- Calculates number of points based on frequency × duration
- Distributes timestamps evenly across the time range
- Saves all generated data points to CSV file

**Usage:**
```bash
# Run emulator with API server
python run_simple_emulator.py --config config/unified_device_config.yaml

# Generate data instantly and save to CSV
python run_simple_emulator.py --generate-csv output.csv --duration 60
```

---

## 2. Data Manager and REST Server

### Overview

The data manager handles storage and analysis of device data streams, while the REST server exposes device data and control endpoints via HTTP API.

### Components

#### 2.1 Data Manager (`DataManager`)

The `DataManager` class (`src/qt_client/data_manager.py`) provides centralized data storage and analytics:

**Core Data Structures:**

- **`DataPoint`**: Represents a single data point
  - `value`: The actual data value (any type)
  - `timestamp`: When the data was generated
  - `unit`: Unit of measurement
  - `metadata`: Additional metadata dictionary

- **`DataStream`**: Collection of data points for a device/data type pair
  - Uses `deque` with maxlen=10000 to limit memory usage
  - Provides methods to get latest value, filter by time range
  - Maintains `last_update` timestamp

**Features:**
- Stores data streams organized by `device_id` and `data_type`
- Processes data from API responses or CSV files
- Provides analytics methods (average, median, standard deviation, trends)
- Supports time-windowed analysis
- Anomaly detection using z-score method

**Key Methods:**
- `process_data_batch()`: Process multiple data points at once
- `get_data_stream()`: Get stream for specific device/data type
- `get_all_data_streams()`: Get all streams
- `get_latest_data()`: Get latest values for all streams

**Analytics Capabilities:**
- Calculate statistics over time windows (1 minute, 5 minutes, all data)
- Trend analysis (increasing, decreasing, stable)
- Min/max detection
- Anomaly detection with configurable threshold

#### 2.2 REST API Server (`RestApiServer`)

The `RestApiServer` class (`src/device_emulator/api/rest_server.py`) provides HTTP endpoints for accessing device data:

**Endpoints:**

- **`GET /health`**: Health check endpoint
  - Returns server status and emulator information

- **`GET /devices`**: Get information about all devices
  - Returns device IDs, names, types, available data types

- **`GET /devices/{device_id}`**: Get information about specific device
  - Returns detailed device information including current values

- **`GET /data`**: Get latest data from all devices
  - Returns all latest data points organized by device

- **`GET /data/{device_id}`**: Get latest data from specific device
  - Returns all data types for the specified device

- **`GET /data/{device_id}/{data_type}`**: Get specific data type from device
  - Returns latest data point for the specified device/data type combination

- **`GET /api`**: API documentation
  - Returns JSON documentation of all available endpoints

- **`GET /stop`**: Stop the emulator
  - Gracefully shuts down the emulator

**Response Format:**
All endpoints return JSON with:
- Requested data
- Timestamp of the response
- Error messages (if applicable)

**Example Response:**
```json
{
  "data": {
    "temp_sensor_001": {
      "temperature": {
        "value": 22.5,
        "timestamp": "2025-01-15T10:30:00",
        "unit": "°C",
        "metadata": {}
      }
    }
  },
  "timestamp": "2025-01-15T10:30:00"
}
```

**Server Configuration:**
- Default host: `localhost`
- Default port: `8080`
- Uses `aiohttp` for async HTTP handling
- Runs in the same event loop as the emulator

---

## 3. API Client

### Overview

The API client is a PyQt6-based graphical application for connecting to the device emulator, visualizing data, and performing analysis.

### Components

#### 3.1 API Client Thread (`ApiClientThread`)

The `ApiClientThread` class (`src/qt_client/api_client_thread.py`) handles all API communication:

**Features:**
- Runs in a separate thread to avoid blocking the UI
- Uses `aiohttp` for async HTTP requests
- Manages a centralized `DataManager` instance
- Supports scheduled data fetching at configurable intervals
- Emits Qt signals for responses and errors

**Key Methods:**
- `make_health_check()`: Check server connectivity
- `make_devices_request()`: Get all devices
- `make_data_request()`: Get all data
- `make_device_data_request()`: Get data for specific device
- `make_specific_data_request()`: Get specific data type
- `start_scheduled_data_fetching()`: Start automatic data fetching
- `stop_scheduled_data_fetching()`: Stop automatic fetching

**Data Flow:**
1. API requests are made asynchronously
2. Responses are processed and stored in `DataManager`
3. Qt signals notify the UI of new data
4. UI updates automatically via timer-based refresh

#### 3.2 Main Application (`DeviceEmulatorClient`)

The `DeviceEmulatorClient` class (`src/qt_client/api_client.py`) is the main Qt application window:

**Tabs:**

1. **API Management Tab**
   - Server connection settings
   - API endpoint selection and testing
   - Request/response display
   - Device list reference

2. **CSV Loader Tab**
   - Load data from CSV files
   - Preview CSV content
   - Parse and import data into DataManager
   - Supports same format as API data (device_id, data_type, value, timestamp, unit, metadata)

3. **Data Visualization Tab**
   - Device data table showing:
     - Device ID, Data Type, Latest Value, Unit, Number of Points, Select checkbox
   - Historical data chart with:
     - Time-based line charts
     - Multiple series support
     - Time range selection via mouse drag
     - Auto-refresh capability
   - Controls for data fetching and chart management

4. **Data Analysis Tab**
   - Data series table with statistics columns:
     - Device ID, Data Type, Latest Value, Unit, Number of Points, Select, Min, Max, Mean, Std Dev
   - Calculate statistics for selected series
   - Export selected series to CSV
   - Refresh data functionality

**Key Features:**

- **Connection Management**: Connect/disconnect from emulator server
- **Data Visualization**: Interactive charts with QtCharts
- **Time Range Selection**: Select time ranges directly on chart by dragging
- **CSV Import/Export**: Load data from CSV or export analysis results
- **Statistical Analysis**: Calculate min, max, mean, standard deviation
- **Auto-refresh**: Periodic updates from DataManager
- **Multi-series Charts**: Display multiple data series simultaneously with different colors

**Chart Features:**
- Custom `HistoricalDataChart` widget
- Supports multiple value axes (for different units)
- Time axis with timestamp display
- Series selection via checkboxes
- Time range filtering
- Clear selection functionality

**Data Flow:**
1. User connects to server via API Management tab
2. `ApiClientThread` fetches data periodically
3. Data is stored in `DataManager`
4. UI timer refreshes tables and charts every 500ms
5. User can select series for visualization or analysis
6. Statistics can be calculated and exported

**CSV Format:**
The application supports CSV files with the following format:
```csv
device_id,data_type,value,timestamp,unit,metadata
temp_sensor_001,temperature,22.5,2025-01-15T10:30:00,°C,{}
```

**Export Format:**
Analysis results are exported with table columns:
```csv
Device ID,Data Type,Latest Value,Unit,Number of Points,Min,Max,Mean,Std Dev
```

---

## Usage Examples

### Running the Emulator

```bash
# Start emulator with default config
python run_simple_emulator.py

# Start with custom config
python run_simple_emulator.py --config config/unified_device_config.yaml

# Generate data and save to CSV (no API server)
python run_simple_emulator.py --generate-csv output.csv --duration 60

# List available devices
python run_simple_emulator.py --list-devices
```

### Running the API Client

```bash
# Start Qt client
python launch_qt_client.py

# Or with logging level
python launch_qt_client.py --log-level DEBUG
```

### Workflow

1. **Start the emulator**: Run `run_simple_emulator.py` to start generating device data
2. **Connect client**: Open Qt client and connect to `http://localhost:8080`
3. **Visualize data**: Select data series in Data Visualization tab to view charts
4. **Analyze data**: Use Data Analysis tab to calculate statistics
5. **Export results**: Export analysis results to CSV for further processing

---

## Architecture Summary

The system follows a modular architecture:

```
┌─────────────────┐
│  Config Files   │ (YAML configuration)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Config Loader   │ (Validates and loads config)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Simple Emulator │ (Manages devices, generates data)
└────────┬────────┘
         │
         ├─────────────────┐
         ▼                 ▼
┌─────────────────┐  ┌──────────────┐
│  REST Server    │  │  CSV Export  │
│  (HTTP API)     │  │  (Optional)  │
└────────┬────────┘  └──────────────┘
         │
         ▼
┌─────────────────┐
│ API Client      │ (Qt Application)
│  Thread         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Manager    │ (Stores and analyzes data)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Qt UI           │ (Visualization and Analysis)
└─────────────────┘
```

---

## Dependencies

- **PyQt6**: GUI framework
- **PyQt6-Charts**: Chart visualization (optional)
- **aiohttp**: Async HTTP server and client
- **pydantic**: Data validation
- **PyYAML**: YAML configuration parsing

See `requirements.txt` for complete list.
