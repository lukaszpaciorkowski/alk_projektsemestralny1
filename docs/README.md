# Device Emulator and Qt Client Documentation

This project provides a comprehensive solution for device emulation and data visualization using Python and Qt.

## Project Structure

```
├── src/                          # Source code
│   ├── device_emulator/         # Device emulation module
│   │   ├── core/               # Core emulator components
│   │   ├── protocols/          # Communication protocols
│   │   └── simulators/         # Device simulators
│   ├── client/                 # Qt client application
│   │   ├── ui/                 # User interface components
│   │   ├── data/               # Data handling
│   │   └── visualization/      # Data visualization
│   └── shared/                 # Shared utilities
│       ├── models/             # Data models
│       ├── utils/              # Utility functions
│       └── communication/      # Communication utilities
├── tests/                      # Test suite
├── docs/                       # Documentation
├── config/                     # Configuration files
├── examples/                   # Example usage
└── scripts/                    # Utility scripts
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Qt 6.x (PyQt6 or PySide6)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the device emulator:
   ```bash
   python scripts/run_emulator.py
   ```

4. Run the Qt client:
   ```bash
   python scripts/run_client.py
   ```

## Features

### Device Emulator
- Support for multiple device types
- Configurable communication protocols
- Realistic data simulation with noise and drift
- Extensible architecture for custom devices

### Qt Client
- Modern Qt-based user interface
- Real-time data visualization
- Configurable charts and graphs
- Data export capabilities

## Configuration

Configuration files are located in the `config/` directory:
- `default.yaml` - Default configuration
- `local.yaml` - Local overrides (create from `local.yaml.example`)

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/ tests/
```

### Type Checking
```bash
mypy src/
```

## License

MIT License - see LICENSE file for details.
