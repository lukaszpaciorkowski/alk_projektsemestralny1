#!/usr/bin/env python3
"""
Simple Qt application for connecting to the device emulator REST API
"""

import sys
import json
import logging
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QTextEdit, QGroupBox, QGridLayout,
                             QMessageBox, QSplitter, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFrame, QCheckBox,
                             QScrollArea, QSizePolicy, QSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QPalette, QColor, QPen, QBrush

# Try to import QtCharts, fallback to basic widget if not available
try:
    from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
    CHARTS_AVAILABLE = True
except ImportError:
    # Fallback: create a simple placeholder widget
    class QChartView(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
            self.setMinimumSize(400, 200)
            
        def paintEvent(self, event):
            """Custom paint event to show message without layout conflicts"""
            super().paintEvent(event)
            from PyQt6.QtGui import QPainter, QFont
            painter = QPainter(self)
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                           "QtCharts not available.\nInstall PyQt6-Charts for chart functionality.")
    
    class QChart:
        def __init__(self): pass
        def setTitle(self, title): pass
        def legend(self): return type('obj', (object,), {'setVisible': lambda x: None, 'setAlignment': lambda x: None})()
        def addAxis(self, axis, alignment): pass
        def addSeries(self, series): pass
        def removeSeries(self, series): pass
    
    class QLineSeries:
        def __init__(self): 
            self.points = []
        def setName(self, name): pass
        def setColor(self, color): pass
        def clear(self): self.points.clear()
        def append(self, x, y): self.points.append((x, y))
        def attachAxis(self, axis): pass
        def count(self): return len(self.points)
        def at(self, index): return type('obj', (object,), {'x': lambda: self.points[index][0], 'y': lambda: self.points[index][1]})()
    
    class QValueAxis:
        def __init__(self): pass
        def setTitleText(self, text): pass
        def setFormat(self, fmt): pass
        def setRange(self, min_val, max_val): pass
    
    class QDateTimeAxis:
        def __init__(self): pass
        def setTitleText(self, text): pass
        def setFormat(self, fmt): pass
        def setRange(self, min_val, max_val): pass
    
    CHARTS_AVAILABLE = False

# Import handling for both package and direct execution
try:
    from .api_client_thread import ApiClientThread
    from .data_manager import DataManager, DataPoint
except ImportError:
    # Fallback for direct execution
    from api_client_thread import ApiClientThread
    from data_manager import DataManager, DataPoint


class HistoricalDataChart(QChartView):
    """Custom chart widget for displaying historical data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if CHARTS_AVAILABLE:
            self.chart = QChart()
            self.setChart(self.chart)
            self.chart.setTitle("Historical Data")
            self.chart.legend().setVisible(True)
            self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
            
            # Create axes
            self.time_axis = QDateTimeAxis()
            self.time_axis.setFormat("hh:mm:ss")
            self.time_axis.setTitleText("Time")
            
            self.value_axis = QValueAxis()
            self.value_axis.setTitleText("Value")
            
            self.chart.addAxis(self.time_axis, Qt.AlignmentFlag.AlignBottom)
            self.chart.addAxis(self.value_axis, Qt.AlignmentFlag.AlignLeft)
        else:
            # Fallback mode - just show a message
            self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
            self.setMinimumSize(400, 200)
        
        # Store series for updates
        self.series_dict = {}
    
    def paintEvent(self, event):
        """Custom paint event for fallback mode"""
        super().paintEvent(event)
        if not CHARTS_AVAILABLE:
            from PyQt6.QtGui import QPainter, QFont
            painter = QPainter(self)
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                           "QtCharts not available.\nInstall PyQt6-Charts for chart functionality.")
        
    def add_data_series(self, device_id: str, data_type: str, data_points: List[DataPoint], color: QColor = None):
        """Add or update a data series"""
        try:
            print(f"DEBUG: add_data_series called - Device: {device_id}, Data Type: {data_type}, Points: {len(data_points)}")
            
            if not CHARTS_AVAILABLE:
                print("WARNING: Charts not available, cannot add series")
                return
                
            series_key = f"{device_id}#{data_type}"
            print(f"DEBUG: Series key: {series_key}")
            
            if series_key in self.series_dict:
                # Update existing series
                print("DEBUG: Updating existing series")
                series = self.series_dict[series_key]
                series.clear()
            else:
                # Create new series
                print("DEBUG: Creating new series")
                series = QLineSeries()
                series.setName(f"{device_id} - {data_type}")
                if color:
                    series.setColor(color)
                    print(f"DEBUG: Set series color: {color}")
                self.chart.addSeries(series)
                series.attachAxis(self.time_axis)
                series.attachAxis(self.value_axis)
                self.series_dict[series_key] = series
                print("DEBUG: Series added to chart")
            
            # Add data points
            valid_points = 0
            for point in data_points:
                if isinstance(point.value, (int, float)):
                    # Convert Python datetime to milliseconds since epoch
                    timestamp_ms = int(point.timestamp.timestamp() * 1000)
                    series.append(timestamp_ms, point.value)
                    valid_points += 1
                else:
                    print(f"WARNING: Skipping non-numeric value: {point.value}")
            
            print(f"DEBUG: Added {valid_points} valid data points to series")
            
            # Update axes ranges
            self._update_axes()
            print("DEBUG: Axes updated")
            
        except Exception as e:
            print(f"ERROR in add_data_series: {e}")
            import traceback
            traceback.print_exc()
    
    def remove_data_series(self, device_id: str, data_type: str):
        """Remove a data series"""
        if not CHARTS_AVAILABLE:
            return
            
        series_key = f"{device_id}#{data_type}"
        if series_key in self.series_dict:
            series = self.series_dict[series_key]
            self.chart.removeSeries(series)
            del self.series_dict[series_key]
            self._update_axes()
    
    def clear_all_series(self):
        """Clear all data series"""
        if not CHARTS_AVAILABLE:
            return
            
        for series in self.series_dict.values():
            self.chart.removeSeries(series)
        self.series_dict.clear()
        self._update_axes()
    
    def _update_axes(self):
        """Update axis ranges based on data"""
        if not CHARTS_AVAILABLE or not self.series_dict:
            return
        
        min_time = float('inf')
        max_time = float('-inf')
        min_value = float('inf')
        max_value = float('-inf')
        
        for series in self.series_dict.values():
            if series.count() > 0:
                min_time = min(min_time, series.at(0).x())
                max_time = max(max_time, series.at(series.count() - 1).x())
                
                for i in range(series.count()):
                    min_value = min(min_value, series.at(i).y())
                    max_value = max(max_value, series.at(i).y())
        
        if min_time != float('inf') and max_time != float('-inf'):
            # Convert milliseconds since epoch to QDateTime objects
            from PyQt6.QtCore import QDateTime
            min_qdatetime = QDateTime.fromMSecsSinceEpoch(int(min_time))
            max_qdatetime = QDateTime.fromMSecsSinceEpoch(int(max_time))
            self.time_axis.setRange(min_qdatetime, max_qdatetime)
        
        if min_value != float('inf') and max_value != float('-inf'):
            # Add some padding to the value range
            padding = (max_value - min_value) * 0.1
            self.value_axis.setRange(min_value - padding, max_value + padding)


class DeviceEmulatorClient(QMainWindow):
    """Main window for the device emulator API client"""
    
    def __init__(self):
        super().__init__()
        self.api_thread = None
        self.data_manager = None
        self.historical_chart = None
        self.device_data_table = None
        self.selected_series = set()  # Track selected data series for chart
        
        # Timer for periodic UI updates from DataManager
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self.refresh_ui_from_data_manager)
        self.ui_update_timer.setInterval(500)  # Update every 2 seconds
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Device Emulator API Client")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create connection settings
        self.create_connection_group(main_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create API Management tab
        self.create_api_management_tab()
        
        # Create Data Visualization tab
        self.create_visualization_tab()
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
    def create_connection_group(self, parent_layout):
        """Create connection settings group"""
        group = QGroupBox("Server Connection")
        layout = QGridLayout(group)
        
        # Server URL
        layout.addWidget(QLabel("Server URL:"), 0, 0)
        self.server_url_edit = QLineEdit("http://localhost:8080")
        layout.addWidget(self.server_url_edit, 0, 1)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_to_server)
        layout.addWidget(self.connect_btn, 0, 2)
        
        # Connection status
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.connection_status, 0, 3)
        
        parent_layout.addWidget(group)
    
    def create_api_management_tab(self):
        """Create the API Management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Create API request panel
        self.create_request_panel(splitter)
        
        # Create response panel
        self.create_response_panel(splitter)
        
        # Set splitter proportions
        splitter.setSizes([400, 800])
        
        self.tab_widget.addTab(tab, "API Management")
        
    def create_visualization_tab(self):
        """Create the Data Visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create splitter for visualization content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Create device data table panel (left side)
        self.create_device_data_panel(splitter)
        
        # Create historical chart panel (right side)
        self.create_chart_panel(splitter)
        
        # Set splitter proportions
        splitter.setSizes([400, 1000])
        
        self.tab_widget.addTab(tab, "Data Visualization")
        
    def create_device_data_panel(self, parent):
        """Create the device data table panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Device data table group
        devices_group = QGroupBox("Device Data")
        devices_layout = QVBoxLayout(devices_group)
        
        # Create device data table
        self.device_data_table = QTableWidget()
        self.device_data_table.setColumnCount(6)
        self.device_data_table.setHorizontalHeaderLabels([
            "Device ID", "Data Type", "Latest Value", "Unit", "Timestamp", "Select"
        ])
        self.device_data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.device_data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Connect selection change to update chart
        self.device_data_table.itemChanged.connect(self.on_device_selection_changed)
        
        devices_layout.addWidget(self.device_data_table)
        
        # Add control buttons and interval setting
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.refresh_device_data)
        button_layout.addWidget(refresh_btn)
        
        self.auto_fetch_btn = QPushButton("Start Auto Fetch")
        self.auto_fetch_btn.clicked.connect(self.toggle_auto_fetch)
        self.auto_fetch_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.auto_fetch_btn)
        
        devices_layout.addLayout(button_layout)
        
        # Add interval control
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Auto Fetch Interval (seconds):"))
        
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(300)  # Max 5 minutes
        self.interval_spinbox.setValue(10)  # Default 10 seconds
        self.interval_spinbox.setSuffix("s")
        self.interval_spinbox.setToolTip("Set the interval for automatic data fetching (1-300 seconds)")
        self.interval_spinbox.valueChanged.connect(self.on_interval_changed)
        interval_layout.addWidget(self.interval_spinbox)
        
        interval_layout.addStretch()
        devices_layout.addLayout(interval_layout)
        
        layout.addWidget(devices_group)
        parent.addWidget(widget)
        
    def create_chart_panel(self, parent):
        """Create the historical chart panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Chart group
        chart_group = QGroupBox("Historical Data Chart")
        chart_layout = QVBoxLayout(chart_group)
        
        # Create historical chart
        self.historical_chart = HistoricalDataChart()
        chart_layout.addWidget(self.historical_chart)
        
        # Add chart controls
        controls_layout = QHBoxLayout()
        
        clear_chart_btn = QPushButton("Clear Chart")
        clear_chart_btn.clicked.connect(self.clear_chart)
        controls_layout.addWidget(clear_chart_btn)
        
        auto_refresh_checkbox = QCheckBox("Auto Refresh")
        auto_refresh_checkbox.setChecked(True)
        auto_refresh_checkbox.toggled.connect(self.toggle_auto_refresh)
        controls_layout.addWidget(auto_refresh_checkbox)
        
        controls_layout.addStretch()
        chart_layout.addLayout(controls_layout)
        
        layout.addWidget(chart_group)
        parent.addWidget(widget)
        
    def create_request_panel(self, parent):
        """Create API request panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # API endpoint selection
        endpoint_group = QGroupBox("API Endpoint")
        endpoint_layout = QVBoxLayout(endpoint_group)
        
        self.endpoint_combo = QComboBox()
        self.endpoint_combo.addItems([
            "/health",
            "/devices", 
            "/devices/{device_id}",
            "/data",
            "/data/{device_id}",
            "/data/{device_id}/{data_type}",
            "/api",
            "/stop"
        ])
        self.endpoint_combo.currentTextChanged.connect(self.on_endpoint_changed)
        endpoint_layout.addWidget(self.endpoint_combo)
        
        # Custom endpoint input
        self.custom_endpoint_edit = QLineEdit()
        self.custom_endpoint_edit.setPlaceholderText("Enter custom endpoint (e.g., /devices/temp_sensor_001)")
        endpoint_layout.addWidget(self.custom_endpoint_edit)
        
        layout.addWidget(endpoint_group)
        
        # Parameters
        params_group = QGroupBox("Parameters")
        params_layout = QVBoxLayout(params_group)
        
        self.params_text = QTextEdit()
        self.params_text.setMaximumHeight(100)
        self.params_text.setPlaceholderText("Enter JSON parameters (for POST requests)")
        params_layout.addWidget(self.params_text)
        
        layout.addWidget(params_group)
        
        # Request buttons
        button_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("Send Request")
        self.send_btn.clicked.connect(self.send_request)
        self.send_btn.setEnabled(False)
        button_layout.addWidget(self.send_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_request)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # Device list (for reference)
        devices_group = QGroupBox("Available Devices")
        devices_layout = QVBoxLayout(devices_group)
        
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(3)
        self.devices_table.setHorizontalHeaderLabels(["Device ID", "Name", "Type"])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        devices_layout.addWidget(self.devices_table)
        
        layout.addWidget(devices_group)
        
        parent.addWidget(widget)
        
    def create_response_panel(self, parent):
        """Create response display panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Response display
        response_group = QGroupBox("Response")
        response_layout = QVBoxLayout(response_group)
        
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setFont(QFont("Consolas", 10))
        response_layout.addWidget(self.response_text)
        
        layout.addWidget(response_group)
        
        # Data visualization
        data_group = QGroupBox("Data Visualization")
        data_layout = QVBoxLayout(data_group)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(["Device", "Data Type", "Value", "Unit"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        data_layout.addWidget(self.data_table)
        
        layout.addWidget(data_group)
        
        parent.addWidget(widget)
        
    def connect_to_server(self):
        """Connect to the server"""
        server_url = self.server_url_edit.text().strip()
        if not server_url:
            QMessageBox.warning(self, "Error", "Please enter a server URL")
            return
            
        try:
            # Stop existing connection
            if self.api_thread:
                self.api_thread.stop()
            
            # Stop UI update timer
            self.ui_update_timer.stop()
                
            # Create new centralized API client
            self.api_thread = ApiClientThread(server_url)
            self.api_thread.response_received.connect(self.on_response_received)
            self.api_thread.error_occurred.connect(self.on_error_occurred)
            self.api_thread.health_check_passed.connect(self.on_health_check_passed)
            self.api_thread.health_check_failed.connect(self.on_health_check_failed)
            self.api_thread.start()
            
            # Wait for the API thread to be ready
            if not self.api_thread.wait_for_ready(timeout=5.0):
                QMessageBox.critical(self, "Connection Error", "Failed to initialize API client thread")
                return
            
            # Get DataManager from ApiClientThread (centralized data storage)
            self.data_manager = self.api_thread.get_data_manager()
            
            # Start UI update timer to periodically refresh from DataManager
            self.ui_update_timer.start()
            
            # Update UI immediately
            self.connection_status.setText("Connecting...")
            self.connection_status.setStyleSheet("color: orange; font-weight: bold;")
            self.send_btn.setEnabled(True)
            self.statusBar().showMessage(f"Connecting to {server_url}...")
            
            # Test connection with health check
            self.test_connection()
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {str(e)}")
            
    def test_connection(self):
        """Test the connection with a health check"""
        if self.api_thread:
            # Use a timer to delay the health check slightly to ensure the thread is ready
            QTimer.singleShot(500, self._send_health_check)
    
    def _send_health_check(self):
        """Send health check request"""
        if self.api_thread:
            self.api_thread.make_health_check()
    
    
    def on_health_check_passed(self):
        """Handle successful health check"""
        self.connection_status.setText("Connected")
        self.connection_status.setStyleSheet("color: green; font-weight: bold;")
        self.statusBar().showMessage("Connected successfully")
    
    def on_health_check_failed(self, error: str):
        """Handle failed health check"""
        self.connection_status.setText("Connection Failed")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        self.statusBar().showMessage(f"Connection failed: {error}")
        QMessageBox.warning(self, "Connection Failed", f"Health check failed: {error}")
            
    def on_endpoint_changed(self, endpoint):
        """Handle endpoint selection change"""
        if endpoint.startswith("/devices/") and "{" in endpoint:
            self.custom_endpoint_edit.setText("/devices/temp_sensor_001")
        elif endpoint.startswith("/data/") and "{" in endpoint:
            self.custom_endpoint_edit.setText("/data/temp_sensor_001")
        else:
            self.custom_endpoint_edit.clear()
            
    def send_request(self):
        """Send API request"""
        if not self.api_thread:
            QMessageBox.warning(self, "Error", "Not connected to server")
            return
            
        if not self.api_thread.is_running or not self.api_thread.session:
            QMessageBox.warning(self, "Error", "API client not ready. Please wait and try again.")
            return
            
        # Additional check for shutdown state
        if hasattr(self.api_thread, 'shutdown_event') and self.api_thread.shutdown_event.is_set():
            QMessageBox.warning(self, "Error", "API client is shutting down. Please reconnect.")
            return
            
        # Get endpoint
        if self.custom_endpoint_edit.text().strip():
            endpoint = self.custom_endpoint_edit.text().strip()
        else:
            endpoint = self.endpoint_combo.currentText()
            
        # Get parameters
        params_text = self.params_text.toPlainText().strip()
        params = None
        if params_text:
            try:
                params = json.loads(params_text)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "JSON Error", f"Invalid JSON: {str(e)}")
                return
        
        # Use appropriate method based on endpoint
        if endpoint == "/health":
            self.api_thread.make_health_check()
        elif endpoint == "/devices":
            self.api_thread.make_devices_request()
        elif endpoint.startswith("/devices/") and not endpoint.endswith("/devices"):
            device_id = endpoint.split("/")[-1]
            self.api_thread.make_device_request(device_id)
        elif endpoint == "/data":
            self.api_thread.make_data_request()
        elif endpoint.startswith("/data/") and endpoint.count("/") == 2:
            device_id = endpoint.split("/")[-1]
            self.api_thread.make_device_data_request(device_id)
        elif endpoint.startswith("/data/") and endpoint.count("/") == 3:
            parts = endpoint.split("/")
            device_id = parts[2]
            data_type = parts[3]
            self.api_thread.make_specific_data_request(device_id, data_type)
        elif endpoint == "/api":
            self.api_thread.make_api_docs_request()
        elif endpoint == "/stop":
            self.api_thread.make_stop_request()
        else:
            # Generic request for custom endpoints
            self.api_thread.make_request(endpoint, "GET", params)
            
        self.statusBar().showMessage(f"Sending request to {endpoint}...")
        
    def clear_request(self):
        """Clear request parameters"""
        self.params_text.clear()
        self.response_text.clear()
        self.data_table.setRowCount(0)
        
    def on_response_received(self, data, endpoint):
        """Handle API response"""
        # Display raw response
        self.response_text.setPlainText(json.dumps(data, indent=2))
        
        # Update status
        self.statusBar().showMessage(f"Response received from {endpoint}")
        
        # Handle specific endpoints
        if endpoint == "/devices":
            self.update_devices_table(data.get("devices", {}))
        elif endpoint.startswith("/data"):
            self.update_data_table(data)
            
    def on_error_occurred(self, error, endpoint):
        """Handle API error"""
        self.response_text.setPlainText(f"Error: {error}")
        self.statusBar().showMessage(f"Error from {endpoint}: {error}")
        QMessageBox.warning(self, "API Error", f"Request failed: {error}")
    
    def refresh_ui_from_data_manager(self):
        """Periodically refresh UI with data from DataManager"""
        if self.data_manager:
            # Update data tables
            self.update_data_table_from_manager()
            self.update_device_data_table()
            
            # Update chart for selected series
            for series_key in self.selected_series:
                parts = series_key.split('#', 1)
                if len(parts) == 2:
                    device_id, data_type = parts
                    # Only update chart if data is available
                    if self.data_manager and self.data_manager.get_data_stream(device_id, data_type):
                        self.update_chart_series(device_id, data_type)
    
    def update_device_data_table(self):
        """Update the device data table in visualization tab"""
        try:
            print("DEBUG: update_device_data_table called")
            
            if not self.data_manager:
                print("ERROR: data_manager is None")
                return
                
            if not self.device_data_table:
                print("ERROR: device_data_table is None")
                return
            
            # Get all data streams
            all_streams = self.data_manager.get_all_data_streams()
            print(f"DEBUG: Found {len(all_streams)} devices with data streams")
            
            # Check if data has changed since last update
            current_data_signature = self._get_data_signature(all_streams)
            if hasattr(self, '_last_data_signature') and current_data_signature == self._last_data_signature:
                print("DEBUG: No new data detected, skipping table update")
                return
            
            # Store current data signature for next comparison
            self._last_data_signature = current_data_signature
            print("DEBUG: New data detected, updating table")
            
            # Count total rows needed
            total_rows = sum(len(device_streams) for device_streams in all_streams.values())
            print(f"DEBUG: Setting table to {total_rows} rows")
            self.device_data_table.setRowCount(total_rows)
            
            row = 0
            for device_id, device_streams in all_streams.items():
                print(f"DEBUG: Processing device {device_id} with {len(device_streams)} data types")
                for data_type, stream in device_streams.items():
                    latest_point = stream.get_latest_data_point()
                    
                    if latest_point:
                        print(f"DEBUG: Adding row {row}: {device_id} - {data_type} = {latest_point.value}")
                        
                        # Device ID
                        self.device_data_table.setItem(row, 0, QTableWidgetItem(device_id))
                        
                        # Data Type
                        self.device_data_table.setItem(row, 1, QTableWidgetItem(data_type))
                        
                        # Latest Value
                        self.device_data_table.setItem(row, 2, QTableWidgetItem(str(latest_point.value)))
                        
                        # Unit
                        self.device_data_table.setItem(row, 3, QTableWidgetItem(latest_point.unit))
                        
                        # Timestamp
                        timestamp_str = latest_point.timestamp.strftime("%H:%M:%S")
                        self.device_data_table.setItem(row, 4, QTableWidgetItem(timestamp_str))
                        
                        # Select checkbox
                        checkbox = QCheckBox()
                        series_key = f"{device_id}#{data_type}"
                        checkbox.setChecked(series_key in self.selected_series)
                        checkbox.stateChanged.connect(lambda state, key=series_key: self.on_series_selection_changed(key, state))
                        self.device_data_table.setCellWidget(row, 5, checkbox)
                        
                        row += 1
                    else:
                        print(f"WARNING: No latest data point for {device_id} - {data_type}")
            
            print(f"DEBUG: Device data table updated with {row} rows")
            
        except Exception as e:
            print(f"ERROR in update_device_data_table: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_data_signature(self, all_streams):
        """Generate a signature for the current data state to detect changes"""
        try:
            signature_parts = []
            
            for device_id, device_streams in all_streams.items():
                for data_type, stream in device_streams.items():
                    latest_point = stream.get_latest_data_point()
                    if latest_point:
                        # Create a signature based on device_id, data_type, value, and timestamp
                        signature_parts.append(f"{device_id}#{data_type}#{latest_point.value}#{latest_point.timestamp.isoformat()}")
            
            # Sort to ensure consistent signature regardless of iteration order
            signature_parts.sort()
            return "|".join(signature_parts)
            
        except Exception as e:
            print(f"ERROR generating data signature: {e}")
            # Return a fallback signature that will always be different
            return f"error_{id(all_streams)}"
    
    def on_series_selection_changed(self, series_key, state):
        """Handle checkbox selection change for data series"""
        try:
            print(f"DEBUG: Series selection changed - {series_key}, state: {state}")
            
            if state == Qt.CheckState.Checked.value:
                self.selected_series.add(series_key)
                print(f"DEBUG: Added {series_key} to selected_series")
                
                # Add series to chart
                parts = series_key.split('#', 1)
                if len(parts) == 2:
                    device_id, data_type = parts
                    print(f"DEBUG: Adding chart series - Device: {device_id}, Data Type: {data_type}")
                    
                    # Check if data is available before trying to update chart
                    if self.data_manager and self.data_manager.get_data_stream(device_id, data_type):
                        self.update_chart_series(device_id, data_type)
                    else:
                        print(f"DEBUG: No data available for {device_id} - {data_type}, skipping chart update")
                        self.statusBar().showMessage(f"No data available for {device_id} - {data_type}. Fetch data first.", 3000)
                else:
                    print(f"ERROR: Invalid series_key format: {series_key}")
            else:
                self.selected_series.discard(series_key)
                print(f"DEBUG: Removed {series_key} from selected_series")
                
                # Remove series from chart
                parts = series_key.split('#', 1)
                if len(parts) == 2:
                    device_id, data_type = parts
                    print(f"DEBUG: Removing chart series - Device: {device_id}, Data Type: {data_type}")
                    self.historical_chart.remove_data_series(device_id, data_type)
                else:
                    print(f"ERROR: Invalid series_key format: {series_key}")
        except Exception as e:
            print(f"ERROR in on_series_selection_changed: {e}")
            import traceback
            traceback.print_exc()
    
    def on_device_selection_changed(self, item):
        """Handle device data table item changes"""
        # This is called when checkboxes change
        # The actual handling is done by on_series_selection_changed
        # This method is kept for compatibility but does nothing
        pass
    
    def update_chart_series(self, device_id, data_type):
        """Update a specific series in the chart"""
        try:
            print(f"DEBUG: update_chart_series called - Device: {device_id}, Data Type: {data_type}")
            
            if not self.data_manager:
                print("ERROR: data_manager is None")
                return
                
            if not self.historical_chart:
                print("ERROR: historical_chart is None")
                return
            
            # Debug: Show all available streams
            all_streams = self.data_manager.get_all_data_streams()
            print(f"DEBUG: Available streams: {list(all_streams.keys())}")
            for dev_id, dev_streams in all_streams.items():
                print(f"DEBUG: Device {dev_id} has streams: {list(dev_streams.keys())}")
            
            stream = self.data_manager.get_data_stream(device_id, data_type)
            if stream:
                print(f"DEBUG: Stream found with {len(stream.data_points)} data points")
                
                # Get all data points from the stream
                data_points = list(stream.data_points)
                if data_points:
                    print(f"DEBUG: Adding {len(data_points)} data points to chart")
                    
                    # Generate a color for this series
                    color = self.get_series_color(device_id, data_type)
                    print(f"DEBUG: Generated color: {color}")
                    
                    self.historical_chart.add_data_series(device_id, data_type, data_points, color)
                    print("DEBUG: Chart series added successfully")
                else:
                    print("WARNING: No data points in stream")
            else:
                print(f"WARNING: Stream not found for {device_id} - {data_type}")
                print(f"DEBUG: This might be because:")
                print(f"DEBUG: 1. No data has been fetched yet for this device/data_type")
                print(f"DEBUG: 2. The device/data_type combination doesn't exist in the emulator")
                print(f"DEBUG: 3. There's a timing issue between table display and data availability")
                print(f"DEBUG: Available devices: {list(all_streams.keys())}")
                if device_id in all_streams:
                    print(f"DEBUG: Device {device_id} exists, available data types: {list(all_streams[device_id].keys())}")
                else:
                    print(f"DEBUG: Device {device_id} does not exist in available streams")
                
                # Show user-friendly message in status bar
                self.statusBar().showMessage(f"No data available for {device_id} - {data_type}. Try fetching data first.", 3000)
                
        except Exception as e:
            print(f"ERROR in update_chart_series: {e}")
            import traceback
            traceback.print_exc()
    
    def get_series_color(self, device_id, data_type):
        """Generate a consistent color for a data series"""
        # Simple hash-based color generation
        hash_val = hash(f"{device_id}_{data_type}")
        colors = [
            QColor(255, 0, 0),    # Red
            QColor(0, 255, 0),    # Green
            QColor(0, 0, 255),    # Blue
            QColor(255, 255, 0),  # Yellow
            QColor(255, 0, 255),  # Magenta
            QColor(0, 255, 255),  # Cyan
            QColor(255, 128, 0),  # Orange
            QColor(128, 0, 255),  # Purple
        ]
        return colors[abs(hash_val) % len(colors)]
    
    def refresh_device_data(self):
        """Refresh the device data table"""
        self.update_device_data_table()
    
    def debug_data_state(self):
        """Debug method to show current data state"""
        if not self.data_manager:
            print("DEBUG: No data_manager available")
            return
        
        print("=== DATA STATE DEBUG ===")
        all_streams = self.data_manager.get_all_data_streams()
        print(f"Total devices: {len(all_streams)}")
        
        for device_id, device_streams in all_streams.items():
            print(f"Device: {device_id}")
            for data_type, stream in device_streams.items():
                latest_point = stream.get_latest_data_point()
                if latest_point:
                    print(f"  - {data_type}: {latest_point.value} ({latest_point.unit}) at {latest_point.timestamp}")
                else:
                    print(f"  - {data_type}: No data points")
        
        print(f"Selected series: {list(self.selected_series)}")
        print("=== END DEBUG ===")
    
    def toggle_auto_fetch(self):
        """Toggle automatic data fetching"""
        if not self.api_thread:
            return
            
        if self.api_thread.is_data_fetching:
            # Stop auto fetching
            self.api_thread.stop_scheduled_data_fetching()
            self.auto_fetch_btn.setText("Start Auto Fetch")
            self.auto_fetch_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            self.interval_spinbox.setEnabled(True)  # Enable interval control when stopped
            self.statusBar().showMessage("Auto data fetching stopped")
        else:
            # Start auto fetching with current interval
            interval_seconds = self.interval_spinbox.value()
            interval_ms = interval_seconds * 1000
            self.api_thread.start_scheduled_data_fetching(interval_ms=interval_ms)
            self.auto_fetch_btn.setText("Stop Auto Fetch")
            self.auto_fetch_btn.setStyleSheet("background-color: #f44336; color: white;")
            self.interval_spinbox.setEnabled(False)  # Disable interval control when running
            self.statusBar().showMessage(f"Auto data fetching started ({interval_seconds}s intervals)")
    
    def on_interval_changed(self, value):
        """Handle interval spinbox value change"""
        if self.api_thread and self.api_thread.is_data_fetching:
            # If auto fetching is active, restart with new interval
            interval_ms = value * 1000
            self.api_thread.set_data_fetch_interval(interval_ms)
            self.statusBar().showMessage(f"Auto fetch interval updated to {value}s")
        else:
            # Just show the new interval value
            self.statusBar().showMessage(f"Auto fetch interval set to {value}s (start auto fetch to apply)")
    
    def clear_chart(self):
        """Clear all data from the chart"""
        if self.historical_chart:
            self.historical_chart.clear_all_series()
        self.selected_series.clear()
        # Uncheck all checkboxes
        if self.device_data_table:
            for row in range(self.device_data_table.rowCount()):
                checkbox = self.device_data_table.cellWidget(row, 5)
                if checkbox:
                    checkbox.setChecked(False)
    
    def toggle_auto_refresh(self, checked):
        """Toggle auto refresh for the chart"""
        # This could be implemented to automatically update the chart
        # when new data arrives
        pass
    
    def update_data_table_from_manager(self):
        """Update data table with DataManager data"""
        if not self.data_manager:
            return
        
        latest_data = self.data_manager.get_latest_data()
        if not latest_data:
            return
        
        # Check if data has changed since last update
        current_data_signature = self._get_latest_data_signature(latest_data)
        if hasattr(self, '_last_latest_data_signature') and current_data_signature == self._last_latest_data_signature:
            print("DEBUG: No new latest data detected, skipping data table update")
            return
        
        # Store current data signature for next comparison
        self._last_latest_data_signature = current_data_signature
        print("DEBUG: New latest data detected, updating data table")
        
        # Count total data points
        total_points = sum(len(device_data) for device_data in latest_data.values() if isinstance(device_data, dict))
        
        self.data_table.setRowCount(total_points)
        row = 0
        
        for device_id, device_data in latest_data.items():
            if isinstance(device_data, dict):
                for data_type, data_point in device_data.items():
                    if isinstance(data_point, dict):
                        self.data_table.setItem(row, 0, QTableWidgetItem(device_id))
                        self.data_table.setItem(row, 1, QTableWidgetItem(data_type))
                        self.data_table.setItem(row, 2, QTableWidgetItem(str(data_point.get("value", ""))))
                        self.data_table.setItem(row, 3, QTableWidgetItem(data_point.get("unit", "")))
                        row += 1
    
    def _get_latest_data_signature(self, latest_data):
        """Generate a signature for the latest data to detect changes"""
        try:
            signature_parts = []
            
            for device_id, device_data in latest_data.items():
                if isinstance(device_data, dict):
                    for data_type, data_point in device_data.items():
                        if isinstance(data_point, dict):
                            # Create signature based on device_id, data_type, value, and timestamp
                            value = data_point.get("value", "")
                            timestamp = data_point.get("timestamp", "")
                            signature_parts.append(f"{device_id}#{data_type}#{value}#{timestamp}")
            
            # Sort to ensure consistent signature regardless of iteration order
            signature_parts.sort()
            return "|".join(signature_parts)
            
        except Exception as e:
            print(f"ERROR generating latest data signature: {e}")
            # Return a fallback signature that will always be different
            return f"error_{id(latest_data)}"
        
    def update_devices_table(self, devices_data):
        """Update devices table with device information"""
        self.devices_table.setRowCount(len(devices_data))
        
        for row, (device_id, device_info) in enumerate(devices_data.items()):
            self.devices_table.setItem(row, 0, QTableWidgetItem(device_id))
            self.devices_table.setItem(row, 1, QTableWidgetItem(device_info.get("device_name", "")))
            self.devices_table.setItem(row, 2, QTableWidgetItem(device_info.get("device_type", "")))
            
    def update_data_table(self, data):
        """Update data table with device data"""
        if "data" in data:
            all_data = data["data"]
        else:
            all_data = {data.get("device_id", "unknown"): data}
            
        # Count total data points
        total_points = sum(len(device_data) for device_data in all_data.values() if isinstance(device_data, dict))
        
        self.data_table.setRowCount(total_points)
        row = 0
        
        for device_id, device_data in all_data.items():
            if isinstance(device_data, dict):
                for data_type, data_point in device_data.items():
                    if isinstance(data_point, dict):
                        self.data_table.setItem(row, 0, QTableWidgetItem(device_id))
                        self.data_table.setItem(row, 1, QTableWidgetItem(data_type))
                        self.data_table.setItem(row, 2, QTableWidgetItem(str(data_point.get("value", ""))))
                        self.data_table.setItem(row, 3, QTableWidgetItem(data_point.get("unit", "")))
                        row += 1
                        
    def closeEvent(self, event):
        """Handle application close"""
        # Stop UI update timer
        if hasattr(self, 'ui_update_timer'):
            self.ui_update_timer.stop()
        
        if self.api_thread:
            self.api_thread.cleanup()
        event.accept()


def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),  # Console output
            logging.FileHandler('qt_client.log', mode='w')  # File output
        ]
    )
    
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = DeviceEmulatorClient()
    window.show()
    
    # Ensure cleanup on application exit
    def cleanup_on_exit():
        if hasattr(window, 'api_thread') and window.api_thread:
            window.api_thread.cleanup()
    
    app.aboutToQuit.connect(cleanup_on_exit)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
