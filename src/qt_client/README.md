# Device Emulator Qt API Client

A simple Qt-based graphical user interface for connecting to and interacting with the Device Emulator REST API.

## Features

- **Server Connection**: Connect to the device emulator REST API server
- **API Endpoint Selection**: Choose from predefined endpoints or enter custom ones
- **Parameter Input**: Send JSON parameters for API requests
- **Response Display**: View API responses in formatted JSON
- **Data Visualization**: Display device data in tabular format
- **Real-time Updates**: Make multiple API calls and view results
- **DataManager**: Automatic periodic data fetching and storage
- **Analytics**: Real-time statistical analysis (average, median, trends, anomalies)
- **Data Export/Import**: Export and import data for analysis

## Installation

1. Install the required dependencies:
```bash
pip install PyQt6 aiohttp
```

2. Make sure the device emulator is running:
```bash
python run_simple_emulator.py
```

## Usage

### Launch the Client

```bash
python src/qt_client/launcher.py
```

Or directly:
```bash
python src/qt_client/api_client.py
```

### Using the Client

1. **Connect to Server**:
   - Enter the server URL (default: `http://localhost:8080`)
   - Click "Connect" to establish connection
   - The status will show "Connected" when successful

2. **Make API Requests**:
   - Select an endpoint from the dropdown or enter a custom one
   - Add JSON parameters if needed (for POST requests)
   - Click "Send Request" to make the API call

3. **View Results**:
   - Raw JSON response is shown in the response panel
   - Device data is displayed in tabular format
   - Available devices are listed in the devices table

### Available Endpoints

- `/health` - Health check
- `/devices` - List all devices
- `/devices/{device_id}` - Get specific device info
- `/data` - Get all device data
- `/data/{device_id}` - Get data from specific device
- `/data/{device_id}/{data_type}` - Get specific data type
- `/api` - API documentation
- `/stop` - Stop the emulator

### Example Usage

1. Connect to `http://localhost:8080`
2. Select `/devices` endpoint
3. Click "Send Request"
4. View the list of available devices
5. Select `/data/temp_sensor_001` endpoint
6. Click "Send Request" to get temperature data

## Interface Overview

- **Connection Panel**: Server URL and connection status
- **Request Panel**: Endpoint selection and parameters
- **Response Panel**: JSON response display
- **Data Visualization**: Tabular data display
- **Devices Table**: Available devices reference

## Troubleshooting

- **Connection Failed**: Ensure the emulator is running on the specified URL
- **API Errors**: Check the response panel for error details
- **Missing Dependencies**: Run `pip install PyQt6 aiohttp`

## DataManager Features

The DataManager provides automatic data collection and analysis:

### Automatic Data Fetching
- Periodically fetches data from `/data` endpoint
- Configurable fetch intervals (default: 5 seconds)
- Thread-safe data storage with incremental updates

### Analytics Capabilities
- **Statistical Analysis**: Average, median, standard deviation
- **Trend Analysis**: Linear regression slope calculation
- **Anomaly Detection**: Z-score based outlier detection
- **Time-based Analysis**: 5-minute and overall statistics
- **Min/Max Values**: Range analysis

### Data Management
- **Incremental Storage**: Keeps last 1000 data points per stream
- **Export/Import**: JSON format data export and import
- **Real-time Updates**: Qt signals for UI integration
- **Thread Safety**: Mutex-protected data access

### Usage Example

```python
from qt_client.data_manager import DataManager

# Create DataManager
data_manager = DataManager("http://localhost:8080", fetch_interval=5000)

# Setup with session
data_manager.setup_session(session, loop)
data_manager.start_fetching()

# Get analytics
analytics = data_manager.get_analytics("temp_sensor_001", "temperature")
print(f"5-minute average: {analytics['average_5min']}")
print(f"Trend: {analytics['trend_5min']}")

# Export data
export_data = data_manager.export_data()
```

## Requirements

- Python 3.8+
- PyQt6
- aiohttp
- Device Emulator running on localhost:8080
