# Installation Guide

## System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: At least 1GB free space

## Installation Methods

### Method 1: Using pip (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd device-emulator-qt-client
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Method 2: Using setup.py

1. **Install in development mode**:
   ```bash
   pip install -e .
   ```

2. **Install with development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

## Qt Installation

### Windows
- PyQt6 is automatically installed with the requirements
- If you encounter issues, install Qt6 separately from the official website

### macOS
```bash
# Using Homebrew
brew install qt6

# Install PyQt6
pip install PyQt6
```

### Linux (Ubuntu/Debian)
```bash
# Install Qt6 development packages
sudo apt-get install qt6-base-dev qt6-tools-dev

# Install PyQt6
pip install PyQt6
```

## Verification

After installation, verify everything works:

1. **Test device emulator**:
   ```bash
   python scripts/run_emulator.py --help
   ```

2. **Test Qt client**:
   ```bash
   python scripts/run_client.py --help
   ```

## Troubleshooting

### Common Issues

1. **Qt/PyQt6 not found**:
   - Ensure Qt6 is properly installed
   - Try installing PySide6 as an alternative: `pip install PySide6`

2. **Import errors**:
   - Verify virtual environment is activated
   - Check Python path includes the src directory

3. **Permission errors**:
   - Run with appropriate permissions
   - Check firewall settings for network communication

### Getting Help

- Check the [FAQ](faq.md)
- Review [Configuration Guide](configuration.md)
- Open an issue on GitHub
