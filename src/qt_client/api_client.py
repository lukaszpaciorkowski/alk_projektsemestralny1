#!/usr/bin/env python3
"""
Simple Qt application for connecting to the device emulator REST API
"""

import sys
import json
import csv
import logging
import argparse
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QTextEdit, QGroupBox, QGridLayout,
                             QMessageBox, QSplitter, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QFrame, QCheckBox,
                             QScrollArea, QSizePolicy, QSpinBox, QFileDialog)
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
    from api_client_thread import ApiClientThread
    from data_manager import DataManager, DataPoint
except ImportError:
    # Fallback for direct execution
    from api_client_thread import ApiClientThread
    from data_manager import DataManager, DataPoint


class HistoricalDataChart(QChartView):
    """Custom chart widget for displaying historical data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"{__name__}.HistoricalDataChart")
        
        if CHARTS_AVAILABLE:
            self.chart = QChart()
            self.setChart(self.chart)
            self.chart.setTitle("Historical Data")
            self.chart.legend().setVisible(True)
            self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
            
            # Create time axis (shared by all series)
            self.time_axis = QDateTimeAxis()
            self.time_axis.setFormat("hh:mm:ss")
            self.time_axis.setTitleText("Time")
            self.time_axis.setLabelsVisible(True)
            self.time_axis.setGridLineVisible(True)
            self.chart.addAxis(self.time_axis, Qt.AlignmentFlag.AlignBottom)
            
            # Store value axes for each unit
            self.value_axes = {}  # unit -> QValueAxis
            self.axis_positions = {}  # unit -> alignment position
            self.next_axis_position = 0  # Track next available position
        else:
            # Fallback mode - just show a message
            self.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
            self.setMinimumSize(400, 200)
        
        # Store series for updates
        self.series_dict = {}
        
        # Store analytics data for each series
        self.analytics_dict = {}  # series_key -> {analytics, stream}
    
    def paintEvent(self, event):
        """Custom paint event for fallback mode and analytics drawing"""
        super().paintEvent(event)
        if not CHARTS_AVAILABLE:
            from PyQt6.QtGui import QPainter, QFont
            painter = QPainter(self)
            painter.setFont(QFont("Arial", 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                           "QtCharts not available.\nInstall PyQt6-Charts for chart functionality.")
            return
        
        # Draw analytics overlays
        if self.analytics_dict:
            from PyQt6.QtGui import QPainter
            viewport = self.viewport()
            if viewport:
                painter = QPainter(viewport)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self._draw_analytics(painter)
                painter.end()
        
    def add_data_series(self, device_id: str, data_type: str, data_points: List[DataPoint], color: QColor = None):
        """Add or update a data series"""
        try:
            self.logger.debug(f"add_data_series called - Device: {device_id}, Data Type: {data_type}, Points: {len(data_points)}")
            
            if not CHARTS_AVAILABLE:
                self.logger.warning("Charts not available, cannot add series")
                return
                
            if not data_points:
                self.logger.warning("No data points provided")
                return
                
            series_key = f"{device_id}#{data_type}"
            self.logger.debug(f"Series key: {series_key}")
            
            # Get the unit from the first data point
            unit = data_points[0].unit if data_points else ""
            self.logger.debug(f"Unit for series: '{unit}'")
            
            # Get or create value axis for this unit
            value_axis = self._get_or_create_value_axis(unit)
            
            if series_key in self.series_dict:
                # Update existing series
                self.logger.debug("Updating existing series")
                series = self.series_dict[series_key]
                series.clear()
            else:
                # Create new series
                self.logger.debug("Creating new series")
                series = QLineSeries()
                series.setName(f"{device_id} - {data_type}")
                if color:
                    series.setColor(color)
                    self.logger.debug(f"Set series color: {color}")
                self.chart.addSeries(series)
                series.attachAxis(self.time_axis)
                series.attachAxis(value_axis)
                self.series_dict[series_key] = series
                self.logger.debug("Series added to chart")
            
            # Add data points
            valid_points = 0
            for point in data_points:
                if isinstance(point.value, (int, float)):
                    # Convert Python datetime to milliseconds since epoch
                    timestamp_ms = int(point.timestamp.timestamp() * 1000)
                    series.append(timestamp_ms, point.value)
                    valid_points += 1
                else:
                    self.logger.warning(f"Skipping non-numeric value: {point.value}")
            
            self.logger.debug(f"Added {valid_points} valid data points to series")
            
            # Update axes ranges
            self._update_axes()
            self.logger.debug("Axes updated")
            
        except Exception as e:
            self.logger.error(f"Error in add_data_series: {e}")
            import traceback
            traceback.print_exc()
    
    def remove_data_series(self, device_id: str, data_type: str):
        """Remove a data series"""
        if not CHARTS_AVAILABLE:
            return
            
        series_key = f"{device_id}#{data_type}"
        if series_key in self.series_dict:
            series = self.series_dict[series_key]
            
            # Get the unit for this series before removing it
            unit = self._get_series_unit(series)
            
            self.chart.removeSeries(series)
            del self.series_dict[series_key]
            
            # Check if we need to remove the axis for this unit
            self._cleanup_unused_axes()
            
            self._update_axes()
    
    def clear_all_series(self):
        """Clear all data series"""
        if not CHARTS_AVAILABLE:
            return
            
        for series in self.series_dict.values():
            self.chart.removeSeries(series)
        self.series_dict.clear()
        
        # Remove all value axes
        for value_axis in self.value_axes.values():
            self.chart.removeAxis(value_axis)
        self.value_axes.clear()
        self.axis_positions.clear()
        self.next_axis_position = 0
        
        self._update_axes()
    
    def _get_or_create_value_axis(self, unit: str):
        """Get or create a value axis for the given unit"""
        if unit not in self.value_axes:
            # Create new value axis for this unit
            value_axis = QValueAxis()
            value_axis.setTitleText(f"Value ({unit})" if unit else "Value")
            # Note: setFormat is not available in PyQt6 QValueAxis
            
            # Determine alignment position (left or right)
            if self.next_axis_position % 2 == 0:
                alignment = Qt.AlignmentFlag.AlignLeft
            else:
                alignment = Qt.AlignmentFlag.AlignRight
            
            self.chart.addAxis(value_axis, alignment)
            self.value_axes[unit] = value_axis
            self.axis_positions[unit] = alignment
            self.next_axis_position += 1
            
            self.logger.debug(f"Created new value axis for unit '{unit}' with alignment {alignment}")
        
        return self.value_axes[unit]
    
    def _get_series_unit(self, series):
        """Get the unit for a given series by finding its attached value axis"""
        if not CHARTS_AVAILABLE:
            return ""
            
        attached_axes = series.attachedAxes()
        for axis in attached_axes:
            if isinstance(axis, QValueAxis):
                # Find which unit this axis belongs to
                for unit, value_axis in self.value_axes.items():
                    if value_axis == axis:
                        return unit
        return ""
    
    def _cleanup_unused_axes(self):
        """Remove axes that are no longer used by any series"""
        if not CHARTS_AVAILABLE:
            return
            
        # Find which units are still in use
        units_in_use = set()
        for series in self.series_dict.values():
            unit = self._get_series_unit(series)
            if unit:
                units_in_use.add(unit)
        
        # Remove axes for units that are no longer in use
        units_to_remove = []
        for unit in self.value_axes.keys():
            if unit not in units_in_use:
                units_to_remove.append(unit)
        
        for unit in units_to_remove:
            value_axis = self.value_axes[unit]
            self.chart.removeAxis(value_axis)
            del self.value_axes[unit]
            del self.axis_positions[unit]
            self.logger.debug(f"Removed unused axis for unit '{unit}'")
        
        # Reset axis position counter if we removed all axes
        if not self.value_axes:
            self.next_axis_position = 0
    
    def _update_axes(self):
        """Update axis ranges based on data"""
        if not CHARTS_AVAILABLE or not self.series_dict:
            return
        
        # Update time axis (shared by all series)
        min_time = float('inf')
        max_time = float('-inf')
        
        for series in self.series_dict.values():
            if series.count() > 0:
                min_time = min(min_time, series.at(0).x())
                max_time = max(max_time, series.at(series.count() - 1).x())
        
        if min_time != float('inf') and max_time != float('-inf'):
            # Convert milliseconds since epoch to QDateTime objects
            from PyQt6.QtCore import QDateTime
            min_qdatetime = QDateTime.fromMSecsSinceEpoch(int(min_time))
            max_qdatetime = QDateTime.fromMSecsSinceEpoch(int(max_time))
            self.time_axis.setRange(min_qdatetime, max_qdatetime)
            self.logger.debug(f"Updated time axis range: {min_qdatetime.toString()} to {max_qdatetime.toString()}")
        else:
            # Set a default range if no data is available
            from PyQt6.QtCore import QDateTime
            now = QDateTime.currentDateTime()
            self.time_axis.setRange(now.addSecs(-3600), now)  # Last hour as default
        
        # Update each value axis based on its associated series
        for unit, value_axis in self.value_axes.items():
            min_value = float('inf')
            max_value = float('-inf')
            
            # Find all series that use this axis
            for series_key, series in self.series_dict.items():
                # Check if this series uses this axis by looking at attached axes
                attached_axes = series.attachedAxes()
                if value_axis in attached_axes and series.count() > 0:
                    for i in range(series.count()):
                        min_value = min(min_value, series.at(i).y())
                        max_value = max(max_value, series.at(i).y())
            
            # Update axis range if we have data
            if min_value != float('inf') and max_value != float('-inf'):
                # Add some padding to the value range
                padding = (max_value - min_value) * 0.1
                if padding == 0:  # Handle case where all values are the same
                    padding = abs(max_value) * 0.1 if max_value != 0 else 1.0
                value_axis.setRange(min_value - padding, max_value + padding)
                self.logger.debug(f"Updated axis for unit '{unit}': {min_value - padding:.2f} to {max_value + padding:.2f}")
    
    def set_analytics(self, device_id: str, data_type: str, analytics: Dict[str, Any], stream):
        """Set analytics data for a series"""
        series_key = f"{device_id}#{data_type}"
        self.analytics_dict[series_key] = {
            'analytics': analytics,
            'stream': stream
        }
        self.update()
        self.repaint()  # Force immediate repaint
    
    def remove_analytics(self, device_id: str, data_type: str):
        """Remove analytics data for a series"""
        series_key = f"{device_id}#{data_type}"
        if series_key in self.analytics_dict:
            del self.analytics_dict[series_key]
        self.update()
        self.repaint()  # Force immediate repaint
    
    def _draw_analytics(self, painter):
        """Draw analytics overlays on the chart"""
        if not CHARTS_AVAILABLE:
            return
        
        from PyQt6.QtCore import QRect
        from PyQt6.QtGui import QPen, QBrush
        
        plot_area = self.chart.plotArea()
        if plot_area.isEmpty():
            return
        
        for series_key, analytics_data in self.analytics_dict.items():
            if series_key not in self.series_dict:
                continue
            
            series = self.series_dict[series_key]
            analytics = analytics_data['analytics']
            stream = analytics_data['stream']
            
            # Get the value axis for this series
            attached_axes = series.attachedAxes()
            value_axis = None
            for axis in attached_axes:
                if isinstance(axis, QValueAxis):
                    value_axis = axis
                    break
            
            if not value_axis:
                continue
            
            # Get axis ranges
            value_min = value_axis.min()
            value_max = value_axis.max()
            time_min = self.time_axis.min().toMSecsSinceEpoch()
            time_max = self.time_axis.max().toMSecsSinceEpoch()
            
            # Get min, max, average from analytics
            min_max_all = analytics.get('min_max_all')
            average_all = analytics.get('average_all')
            std_dev_all = analytics.get('std_dev_all')
            
            if min_max_all and 'min' in min_max_all and 'max' in min_max_all:
                min_val = min_max_all['min']
                max_val = min_max_all['max']
                
                # Draw min line (bold horizontal)
                if min_val >= value_min and min_val <= value_max:
                    y_pos = self._value_to_y(min_val, value_min, value_max, plot_area)
                    pen = QPen(QColor(255, 0, 0), 3)  # Red, bold
                    painter.setPen(pen)
                    painter.drawLine(int(plot_area.left()), int(y_pos), int(plot_area.right()), int(y_pos))
                
                # Draw max line (bold horizontal)
                if max_val >= value_min and max_val <= value_max:
                    y_pos = self._value_to_y(max_val, value_min, value_max, plot_area)
                    pen = QPen(QColor(0, 0, 255), 3)  # Blue, bold
                    painter.setPen(pen)
                    painter.drawLine(int(plot_area.left()), int(y_pos), int(plot_area.right()), int(y_pos))
            
            # Draw average line (bold horizontal)
            if average_all is not None and average_all >= value_min and average_all <= value_max:
                y_pos = self._value_to_y(average_all, value_min, value_max, plot_area)
                pen = QPen(QColor(0, 255, 0), 3)  # Green, bold
                painter.setPen(pen)
                painter.drawLine(int(plot_area.left()), int(y_pos), int(plot_area.right()), int(y_pos))
            
            # Draw standard deviation range (mean ± std dev)
            if average_all is not None and std_dev_all is not None:
                mean_plus_std = average_all + std_dev_all
                mean_minus_std = average_all - std_dev_all
                
                if mean_plus_std >= value_min and mean_minus_std <= value_max:
                    y_plus = self._value_to_y(mean_plus_std, value_min, value_max, plot_area)
                    y_minus = self._value_to_y(mean_minus_std, value_min, value_max, plot_area)
                    
                    # Draw shaded area
                    rect = QRect(
                        int(plot_area.left()),
                        int(min(y_plus, y_minus)),
                        int(plot_area.width()),
                        int(abs(y_plus - y_minus))
                    )
                    brush = QBrush(QColor(255, 255, 0, 100))  # Yellow, semi-transparent
                    painter.fillRect(rect, brush)
                    
                    # Draw lines for std dev range
                    pen = QPen(QColor(255, 255, 0), 2)  # Yellow
                    painter.setPen(pen)
                    painter.drawLine(int(plot_area.left()), int(y_plus), int(plot_area.right()), int(y_plus))
                    painter.drawLine(int(plot_area.left()), int(y_minus), int(plot_area.right()), int(y_minus))
            
            # Draw anomalies as points
            from data_manager import DataAnalytics
            anomalies = DataAnalytics.detect_anomalies(stream, threshold=2.0)
            
            if anomalies:
                pen = QPen(QColor(255, 0, 255), 1)  # Magenta
                brush = QBrush(QColor(255, 0, 255))  # Magenta
                painter.setPen(pen)
                painter.setBrush(brush)
                
                for anomaly in anomalies:
                    if isinstance(anomaly.value, (int, float)) and anomaly.value >= value_min and anomaly.value <= value_max:
                        x_pos = self._time_to_x(anomaly.timestamp, time_min, time_max, plot_area)
                        y_pos = self._value_to_y(anomaly.value, value_min, value_max, plot_area)
                        
                        # Draw circle with radius at least 5px
                        radius = 6
                        painter.drawEllipse(int(x_pos - radius), int(y_pos - radius), radius * 2, radius * 2)
    
    def _value_to_y(self, value: float, value_min: float, value_max: float, plot_area) -> float:
        """Convert a value to y coordinate in plot area"""
        if value_max == value_min:
            return plot_area.center().y()
        ratio = (value - value_min) / (value_max - value_min)
        return plot_area.bottom() - ratio * plot_area.height()
    
    def _time_to_x(self, timestamp: datetime, time_min: float, time_max: float, plot_area) -> float:
        """Convert a timestamp to x coordinate in plot area"""
        timestamp_ms = int(timestamp.timestamp() * 1000)
        if time_max == time_min:
            return plot_area.center().x()
        ratio = (timestamp_ms - time_min) / (time_max - time_min)
        return plot_area.left() + ratio * plot_area.width()


class DeviceEmulatorClient(QMainWindow):
    """Main window for the device emulator API client"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.DeviceEmulatorClient")
        self.api_thread = None
        self.data_manager = None
        self.historical_chart = None
        self.device_data_table = None
        self.selected_series = set()  # Track selected data series for chart
        self.analytics_enabled_series = set()  # Track series with analytics enabled
        self.analysis_data_table = None  # Table for data analysis tab
        self.selected_analysis_series = set()  # Track selected series for analysis
        self.analysis_statistics = {}  # Store calculated statistics: series_key -> {min, max, mean, std_dev}
        
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
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create API Management tab
        self.create_api_management_tab()
        
        # Create CSV Loader tab
        self.create_csv_loader_tab()
        
        # Create Data Visualization tab
        self.create_visualization_tab()
        
        # Create Data Analysis tab
        self.create_data_analysis_tab()
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
    def create_connection_group(self, parent_layout):
        """Create connection settings group"""
        group = QGroupBox("Server Connection")
        
        # Set size policy to prevent vertical expansion
        group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        group.setMaximumHeight(80)  # Constrain height to prevent expansion
        
        layout = QGridLayout(group)
        layout.setContentsMargins(10, 10, 10, 10)  # Add some padding
        
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
        
        # Create connection settings at the top of the tab
        self.create_connection_group(layout)
        
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
    
    def create_csv_loader_tab(self):
        """Create the CSV Loader tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # CSV Loader group
        csv_group = QGroupBox("CSV File Loader")
        csv_layout = QVBoxLayout(csv_group)
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("CSV File:"))
        
        self.csv_file_path = QLineEdit()
        self.csv_file_path.setPlaceholderText("Select a CSV file to load...")
        self.csv_file_path.setReadOnly(True)
        file_layout.addWidget(self.csv_file_path)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_csv_file)
        file_layout.addWidget(browse_btn)
        
        csv_layout.addLayout(file_layout)
        
        # CSV format info
        format_info = QLabel(
            "Expected CSV format: device_id, data_type, value, timestamp, unit (optional), metadata (optional)\n"
            "Headers are optional. Timestamp format: ISO format (YYYY-MM-DDTHH:MM:SS) or Unix timestamp"
        )
        format_info.setWordWrap(True)
        format_info.setStyleSheet("color: #666; font-size: 10pt; padding: 5px;")
        csv_layout.addWidget(format_info)
        
        # Load button
        load_btn = QPushButton("Load CSV Data")
        load_btn.clicked.connect(self.load_csv_data)
        load_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        csv_layout.addWidget(load_btn)
        
        # Status and statistics
        stats_layout = QHBoxLayout()
        self.csv_status_label = QLabel("Status: Ready to load CSV file")
        stats_layout.addWidget(self.csv_status_label)
        
        stats_layout.addStretch()
        csv_layout.addLayout(stats_layout)
        
        layout.addWidget(csv_group)
        
        # Preview table
        preview_group = QGroupBox("CSV Preview (First 10 rows)")
        preview_layout = QVBoxLayout(preview_group)
        
        self.csv_preview_table = QTableWidget()
        self.csv_preview_table.setColumnCount(6)
        self.csv_preview_table.setHorizontalHeaderLabels([
            "Device ID", "Data Type", "Value", "Timestamp", "Unit", "Metadata"
        ])
        self.csv_preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.csv_preview_table.setMaximumHeight(250)
        preview_layout.addWidget(self.csv_preview_table)
        
        layout.addWidget(preview_group)
        
        # Load statistics
        stats_group = QGroupBox("Load Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.csv_stats_text = QTextEdit()
        self.csv_stats_text.setReadOnly(True)
        self.csv_stats_text.setMaximumHeight(150)
        self.csv_stats_text.setFont(QFont("Consolas", 9))
        stats_layout.addWidget(self.csv_stats_text)
        
        layout.addWidget(stats_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "CSV Loader")
        
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
    
    def create_data_analysis_tab(self):
        """Create the Data Analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Data series table group
        table_group = QGroupBox("Data Series")
        table_layout = QVBoxLayout(table_group)
        
        # Create analysis data table with additional columns for statistics
        self.analysis_data_table = QTableWidget()
        self.analysis_data_table.setColumnCount(10)
        self.analysis_data_table.setHorizontalHeaderLabels([
            "Device ID", "Data Type", "Latest Value", "Unit", "Number of Points", 
            "Select", "Min", "Max", "Mean", "Std Dev"
        ])
        self.analysis_data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.analysis_data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        table_layout.addWidget(self.analysis_data_table)
        
        # Add control buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.refresh_analysis_table)
        button_layout.addWidget(refresh_btn)
        
        calculate_stats_btn = QPushButton("Calculate Statistics")
        calculate_stats_btn.clicked.connect(self.calculate_statistics)
        calculate_stats_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
        button_layout.addWidget(calculate_stats_btn)
        
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.export_selected_series_to_csv)
        export_csv_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;")
        button_layout.addWidget(export_csv_btn)
        
        button_layout.addStretch()
        table_layout.addLayout(button_layout)
        
        layout.addWidget(table_group)
        
        self.tab_widget.addTab(tab, "Data Analysis")
        
    def create_device_data_panel(self, parent):
        """Create the device data table panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Device data table group
        devices_group = QGroupBox("Device Data")
        devices_layout = QVBoxLayout(devices_group)
        
        # Create device data table
        self.device_data_table = QTableWidget()
        self.device_data_table.setColumnCount(7)
        self.device_data_table.setHorizontalHeaderLabels([
            "Device ID", "Data Type", "Latest Value", "Unit", "Number of Points", "Select", "Analytics"
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
        
        calculate_analytics_btn = QPushButton("Calculate Analytics")
        calculate_analytics_btn.clicked.connect(self.calculate_and_store_analytics)
        calculate_analytics_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 5px;")
        controls_layout.addWidget(calculate_analytics_btn)
        
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
            
            # Update analysis table if it exists
            if self.analysis_data_table:
                self.update_analysis_data_table()
            
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
            self.logger.debug("update_device_data_table called")
            
            if not self.data_manager:
                self.logger.error("data_manager is None")
                return
                
            if not self.device_data_table:
                self.logger.error("device_data_table is None")
                return
            
            # Get all data streams
            all_streams = self.data_manager.get_all_data_streams()
            self.logger.debug(f"Found {len(all_streams)} devices with data streams")
            
            # Check if data has changed since last update
            current_data_signature = self._get_data_signature(all_streams)
            if hasattr(self, '_last_data_signature') and current_data_signature == self._last_data_signature:
                self.logger.debug("No new data detected, skipping table update")
                return
            
            # Store current data signature for next comparison
            self._last_data_signature = current_data_signature
            self.logger.debug("New data detected, updating table")
            
            # Count total rows needed
            total_rows = sum(len(device_streams) for device_streams in all_streams.values())
            self.logger.debug(f"Setting table to {total_rows} rows")
            self.device_data_table.setRowCount(total_rows)
            
            row = 0
            for device_id, device_streams in all_streams.items():
                self.logger.debug(f"Processing device {device_id} with {len(device_streams)} data types")
                for data_type, stream in device_streams.items():
                    latest_point = stream.get_latest_data_point()
                    
                    if latest_point:
                        self.logger.debug(f"Adding row {row}: {device_id} - {data_type} = {latest_point.value}")
                        
                        # Device ID
                        self.device_data_table.setItem(row, 0, QTableWidgetItem(device_id))
                        
                        # Data Type
                        self.device_data_table.setItem(row, 1, QTableWidgetItem(data_type))
                        
                        # Latest Value
                        self.device_data_table.setItem(row, 2, QTableWidgetItem(str(latest_point.value)))
                        
                        # Unit
                        self.device_data_table.setItem(row, 3, QTableWidgetItem(latest_point.unit))
                        
                        # Number of Points
                        num_points = len(stream.data_points)
                        self.device_data_table.setItem(row, 4, QTableWidgetItem(str(num_points)))
                        
                        # Select checkbox
                        checkbox = QCheckBox()
                        checkbox.setStyleSheet("""
                            QCheckBox::indicator:checked {
                                background-color: red;
                                border: 1px solid black;
                            }
                            QCheckBox::indicator:unchecked {
                                background-color: white;
                                border: 1px solid black;
                            }
                        """)
                        series_key = f"{device_id}#{data_type}"
                        checkbox.setChecked(series_key in self.selected_series)
                        checkbox.stateChanged.connect(lambda state, key=series_key: self.on_series_selection_changed(key, state))
                        self.device_data_table.setCellWidget(row, 5, checkbox)
                        
                        # Analytics checkbox
                        analytics_checkbox = QCheckBox()
                        analytics_checkbox.setStyleSheet("""
                            QCheckBox::indicator:checked {
                                background-color: orange;
                                border: 1px solid black;
                            }
                            QCheckBox::indicator:unchecked {
                                background-color: white;
                                border: 1px solid black;
                            }
                        """)
                        analytics_checkbox.setChecked(series_key in self.analytics_enabled_series)
                        analytics_checkbox.stateChanged.connect(lambda state, key=series_key: self.on_analytics_selection_changed(key, state))
                        self.device_data_table.setCellWidget(row, 6, analytics_checkbox)
                        
                        row += 1
                    else:
                        self.logger.warning(f"No latest data point for {device_id} - {data_type}")
            
            self.logger.debug(f"Device data table updated with {row} rows")
            
        except Exception as e:
            self.logger.error(f"Error in update_device_data_table: {e}")
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
            self.logger.error(f"Error generating data signature: {e}")
            # Return a fallback signature that will always be different
            return f"error_{id(all_streams)}"
    
    def on_series_selection_changed(self, series_key, state):
        """Handle checkbox selection change for data series"""
        try:
            self.logger.debug(f"Series selection changed - {series_key}, state: {state}")
            
            if state == Qt.CheckState.Checked.value:
                self.selected_series.add(series_key)
                self.logger.debug(f"Added {series_key} to selected_series")
                
                # Add series to chart
                parts = series_key.split('#', 1)
                if len(parts) == 2:
                    device_id, data_type = parts
                    self.logger.debug(f"Adding chart series - Device: {device_id}, Data Type: {data_type}")
                    
                    # Check if data is available before trying to update chart
                    if self.data_manager and self.data_manager.get_data_stream(device_id, data_type):
                        self.update_chart_series(device_id, data_type)
                    else:
                        self.logger.debug(f"No data available for {device_id} - {data_type}, skipping chart update")
                        self.statusBar().showMessage(f"No data available for {device_id} - {data_type}. Fetch data first.", 3000)
                else:
                    self.logger.error(f"Invalid series_key format: {series_key}")
            else:
                self.selected_series.discard(series_key)
                self.logger.debug(f"Removed {series_key} from selected_series")
                
                # Remove series from chart
                parts = series_key.split('#', 1)
                if len(parts) == 2:
                    device_id, data_type = parts
                    self.logger.debug(f"Removing chart series - Device: {device_id}, Data Type: {data_type}")
                    self.historical_chart.remove_data_series(device_id, data_type)
                else:
                    self.logger.error(f"Invalid series_key format: {series_key}")
        except Exception as e:
            self.logger.error(f"Error in on_series_selection_changed: {e}")
            import traceback
            traceback.print_exc()
    
    def on_analytics_selection_changed(self, series_key: str, state: int):
        """Handle analytics checkbox selection change"""
        try:
            self.logger.debug(f"Analytics selection changed - {series_key}, state: {state}")
            
            parts = series_key.split('#', 1)
            if len(parts) != 2:
                self.logger.error(f"Invalid series_key format: {series_key}")
                return
            
            device_id, data_type = parts
            
            if state == Qt.CheckState.Checked.value:
                self.analytics_enabled_series.add(series_key)
                self.logger.debug(f"Added {series_key} to analytics_enabled_series")
                
                # Get analytics data and update chart
                if self.data_manager:
                    stream = self.data_manager.get_data_stream(device_id, data_type)
                    if stream and stream.analytics:
                        self.historical_chart.set_analytics(device_id, data_type, stream.analytics, stream)
                    else:
                        self.logger.warning(f"No analytics available for {device_id}.{data_type}. Calculate analytics first.")
                        self.statusBar().showMessage(f"No analytics available for {device_id}.{data_type}. Calculate analytics first.", 3000)
            else:
                self.analytics_enabled_series.discard(series_key)
                self.logger.debug(f"Removed {series_key} from analytics_enabled_series")
                self.historical_chart.remove_analytics(device_id, data_type)
            
            # Refresh chart to show/hide analytics immediately
            self.historical_chart.update()
            self.historical_chart.repaint()  # Force immediate repaint
                
        except Exception as e:
            self.logger.error(f"Error in on_analytics_selection_changed: {e}")
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
            self.logger.debug(f"update_chart_series called - Device: {device_id}, Data Type: {data_type}")
            
            if not self.data_manager:
                self.logger.error("data_manager is None")
                return
                
            if not self.historical_chart:
                self.logger.error("historical_chart is None")
                return
            
            # Debug: Show all available streams
            all_streams = self.data_manager.get_all_data_streams()
            self.logger.debug(f"Available streams: {list(all_streams.keys())}")
            for dev_id, dev_streams in all_streams.items():
                self.logger.debug(f"Device {dev_id} has streams: {list(dev_streams.keys())}")
            
            stream = self.data_manager.get_data_stream(device_id, data_type)
            if stream:
                self.logger.debug(f"Stream found with {len(stream.data_points)} data points")
                
                # Get all data points from the stream
                data_points = list(stream.data_points)
                if data_points:
                    self.logger.debug(f"Adding {len(data_points)} data points to chart")
                    
                    # Generate a color for this series
                    color = self.get_series_color(device_id, data_type)
                    self.logger.debug(f"Generated color: {color}")
                    
                    self.historical_chart.add_data_series(device_id, data_type, data_points, color)
                    self.logger.debug("Chart series added successfully")
                else:
                    self.logger.warning("No data points in stream")
            else:
                self.logger.warning(f"Stream not found for {device_id} - {data_type}")
                self.logger.debug("This might be because:")
                self.logger.debug("1. No data has been fetched yet for this device/data_type")
                self.logger.debug("2. The device/data_type combination doesn't exist in the emulator")
                self.logger.debug("3. There's a timing issue between table display and data availability")
                self.logger.debug(f"Available devices: {list(all_streams.keys())}")
                if device_id in all_streams:
                    self.logger.debug(f"Device {device_id} exists, available data types: {list(all_streams[device_id].keys())}")
                else:
                    self.logger.debug(f"Device {device_id} does not exist in available streams")
                
                # Show user-friendly message in status bar
                self.statusBar().showMessage(f"No data available for {device_id} - {data_type}. Try fetching data first.", 3000)
                
        except Exception as e:
            self.logger.error(f"Error in update_chart_series: {e}")
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
    
    def calculate_and_store_analytics(self):
        """Calculate analytics for all data series and store them with timestamps"""
        try:
            if not self.data_manager:
                QMessageBox.warning(self, "No Data", "No data manager available. Please connect to the server or load CSV data first.")
                return
            
            # Get all data streams
            all_streams = self.data_manager.get_all_data_streams()
            
            if not all_streams:
                QMessageBox.warning(self, "No Data", "No data streams available. Please fetch data first.")
                return
            
            self.logger.info(f"Calculating and storing analytics for all data series")
            
            calculated_count = 0
            failed_count = 0
            
            # Calculate analytics for all data series
            for device_id, device_streams in all_streams.items():
                for data_type, stream in device_streams.items():
                    try:
                        analytics = self.data_manager.calculate_and_store_analytics(device_id, data_type)
                        
                        if analytics:
                            calculated_count += 1
                            analytics_timestamp = analytics.get('calculation_timestamp', 'Unknown')
                            self.logger.debug(f"Stored analytics for {device_id}.{data_type} at {analytics_timestamp}")
                        else:
                            failed_count += 1
                            self.logger.warning(f"Failed to calculate analytics for {device_id}.{data_type}")
                    except Exception as e:
                        failed_count += 1
                        self.logger.error(f"Error calculating analytics for {device_id}.{data_type}: {e}")
                        continue
            
            # Show success message
            message = f"Analytics calculated and stored for {calculated_count} data series(s)."
            if failed_count > 0:
                message += f"\n{failed_count} series(s) failed."
            
            QMessageBox.information(
                self,
                "Analytics Calculated",
                message
            )
            
            # Refresh the device data table to show updated information
            self.update_device_data_table()
            
            # Update analytics on chart if enabled
            for series_key in self.analytics_enabled_series:
                parts = series_key.split('#', 1)
                if len(parts) == 2:
                    device_id, data_type = parts
                    stream = self.data_manager.get_data_stream(device_id, data_type)
                    if stream and stream.analytics:
                        self.historical_chart.set_analytics(device_id, data_type, stream.analytics, stream)
            
        except Exception as e:
            self.logger.error(f"Error calculating analytics: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error calculating analytics: {str(e)}")
    
    def refresh_analysis_table(self):
        """Refresh the analysis data table"""
        self.update_analysis_data_table()
    
    def update_analysis_data_table(self):
        """Update the analysis data table"""
        try:
            self.logger.debug("update_analysis_data_table called")
            
            if not self.data_manager:
                self.logger.error("data_manager is None")
                return
                
            if not self.analysis_data_table:
                self.logger.error("analysis_data_table is None")
                return
            
            # Get all data streams
            all_streams = self.data_manager.get_all_data_streams()
            self.logger.debug(f"Found {len(all_streams)} devices with data streams")
            
            # Count total rows needed
            total_rows = sum(len(device_streams) for device_streams in all_streams.values())
            self.logger.debug(f"Setting analysis table to {total_rows} rows")
            self.analysis_data_table.setRowCount(total_rows)
            
            row = 0
            for device_id, device_streams in all_streams.items():
                self.logger.debug(f"Processing device {device_id} with {len(device_streams)} data types")
                for data_type, stream in device_streams.items():
                    latest_point = stream.get_latest_data_point()
                    
                    if latest_point:
                        series_key = f"{device_id}#{data_type}"
                        
                        # Device ID
                        self.analysis_data_table.setItem(row, 0, QTableWidgetItem(device_id))
                        
                        # Data Type
                        self.analysis_data_table.setItem(row, 1, QTableWidgetItem(data_type))
                        
                        # Latest Value
                        self.analysis_data_table.setItem(row, 2, QTableWidgetItem(str(latest_point.value)))
                        
                        # Unit
                        self.analysis_data_table.setItem(row, 3, QTableWidgetItem(latest_point.unit))
                        
                        # Number of Points
                        num_points = len(stream.data_points)
                        self.analysis_data_table.setItem(row, 4, QTableWidgetItem(str(num_points)))
                        
                        # Select checkbox
                        checkbox = QCheckBox()
                        checkbox.setStyleSheet("""
                            QCheckBox::indicator:checked {
                                background-color: #2196F3;
                                border: 1px solid black;
                            }
                            QCheckBox::indicator:unchecked {
                                background-color: white;
                                border: 1px solid black;
                            }
                        """)
                        checkbox.setChecked(series_key in self.selected_analysis_series)
                        checkbox.stateChanged.connect(lambda state, key=series_key: self.on_analysis_series_selection_changed(key, state))
                        self.analysis_data_table.setCellWidget(row, 5, checkbox)
                        
                        # Statistics columns (Min, Max, Mean, Std Dev)
                        # Get statistics if they exist
                        stats = self.analysis_statistics.get(series_key, {})
                        
                        # Min
                        min_value = stats.get('min', '')
                        self.analysis_data_table.setItem(row, 6, QTableWidgetItem(str(min_value) if min_value != '' else ''))
                        
                        # Max
                        max_value = stats.get('max', '')
                        self.analysis_data_table.setItem(row, 7, QTableWidgetItem(str(max_value) if max_value != '' else ''))
                        
                        # Mean
                        mean_value = stats.get('mean', '')
                        self.analysis_data_table.setItem(row, 8, QTableWidgetItem(str(mean_value) if mean_value != '' else ''))
                        
                        # Std Dev
                        std_dev_value = stats.get('std_dev', '')
                        self.analysis_data_table.setItem(row, 9, QTableWidgetItem(str(std_dev_value) if std_dev_value != '' else ''))
                        
                        row += 1
                    else:
                        self.logger.warning(f"No latest data point for {device_id} - {data_type}")
            
            self.logger.debug(f"Analysis data table updated with {row} rows")
            
        except Exception as e:
            self.logger.error(f"Error in update_analysis_data_table: {e}")
            import traceback
            traceback.print_exc()
    
    def on_analysis_series_selection_changed(self, series_key, state):
        """Handle checkbox selection change for analysis data series"""
        try:
            self.logger.debug(f"Analysis series selection changed - {series_key}, state: {state}")
            
            if state == Qt.CheckState.Checked.value:
                self.selected_analysis_series.add(series_key)
                self.logger.debug(f"Added {series_key} to selected_analysis_series")
            else:
                self.selected_analysis_series.discard(series_key)
                self.logger.debug(f"Removed {series_key} from selected_analysis_series")
                
        except Exception as e:
            self.logger.error(f"Error in on_analysis_series_selection_changed: {e}")
            import traceback
            traceback.print_exc()
    
    def calculate_statistics(self):
        """Calculate statistics (min, max, mean, std dev) for selected data series"""
        try:
            if not self.data_manager:
                QMessageBox.warning(self, "No Data", "No data manager available. Please connect to the server or load CSV data first.")
                return
            
            if not self.selected_analysis_series:
                QMessageBox.warning(self, "No Selection", "Please select at least one data series to calculate statistics.")
                return
            
            self.logger.info(f"Calculating statistics for {len(self.selected_analysis_series)} selected series")
            
            # Calculate statistics for each selected series
            for series_key in self.selected_analysis_series:
                parts = series_key.split('#', 1)
                if len(parts) != 2:
                    self.logger.warning(f"Invalid series_key format: {series_key}")
                    continue
                
                device_id, data_type = parts
                stream = self.data_manager.get_data_stream(device_id, data_type)
                
                if not stream:
                    self.logger.warning(f"Stream not found for {device_id} - {data_type}")
                    continue
                
                # Get all numeric values from the stream
                values = []
                for point in stream.data_points:
                    if isinstance(point.value, (int, float)):
                        values.append(float(point.value))
                
                if not values:
                    self.logger.warning(f"No numeric values found for {device_id} - {data_type}")
                    self.analysis_statistics[series_key] = {
                        'min': '',
                        'max': '',
                        'mean': '',
                        'std_dev': ''
                    }
                    continue
                
                # Calculate statistics
                min_val = min(values)
                max_val = max(values)
                mean_val = statistics.mean(values)
                
                # Calculate standard deviation (handle case with only one value)
                if len(values) > 1:
                    std_dev_val = statistics.stdev(values)
                else:
                    std_dev_val = 0.0
                
                # Store statistics
                self.analysis_statistics[series_key] = {
                    'min': round(min_val, 4),
                    'max': round(max_val, 4),
                    'mean': round(mean_val, 4),
                    'std_dev': round(std_dev_val, 4)
                }
                
                self.logger.debug(f"Statistics for {series_key}: min={min_val}, max={max_val}, mean={mean_val}, std_dev={std_dev_val}")
            
            # Refresh the table to show calculated statistics
            self.update_analysis_data_table()
            
            # Show success message
            QMessageBox.information(
                self,
                "Statistics Calculated",
                f"Successfully calculated statistics for {len(self.selected_analysis_series)} data series(s)."
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error calculating statistics: {str(e)}")
    
    def export_selected_series_to_csv(self):
        """Export selected data series from the analysis table to CSV file"""
        try:
            if not self.analysis_data_table:
                QMessageBox.warning(self, "No Table", "Analysis table is not available.")
                return
            
            if not self.selected_analysis_series:
                QMessageBox.warning(self, "No Selection", "Please select at least one data series to export.")
                return
            
            # Open file dialog to select save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Selected Data Series to CSV",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Ensure .csv extension
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            
            self.logger.info(f"Exporting {len(self.selected_analysis_series)} selected series to {file_path}")
            
            # Collect table data for selected series
            table_rows = []
            
            # Get all rows from the table
            for row in range(self.analysis_data_table.rowCount()):
                # Get the checkbox to check if this series is selected
                checkbox = self.analysis_data_table.cellWidget(row, 5)  # Select column is at index 5
                if not checkbox or not checkbox.isChecked():
                    continue  # Skip unselected rows
                
                # Extract data from table columns
                device_id_item = self.analysis_data_table.item(row, 0)  # Device ID
                data_type_item = self.analysis_data_table.item(row, 1)  # Data Type
                latest_value_item = self.analysis_data_table.item(row, 2)  # Latest Value
                unit_item = self.analysis_data_table.item(row, 3)  # Unit
                num_points_item = self.analysis_data_table.item(row, 4)  # Number of Points
                min_item = self.analysis_data_table.item(row, 6)  # Min
                max_item = self.analysis_data_table.item(row, 7)  # Max
                mean_item = self.analysis_data_table.item(row, 8)  # Mean
                std_dev_item = self.analysis_data_table.item(row, 9)  # Std Dev
                
                # Get text values (handle None items)
                device_id = device_id_item.text() if device_id_item else ""
                data_type = data_type_item.text() if data_type_item else ""
                latest_value = latest_value_item.text() if latest_value_item else ""
                unit = unit_item.text() if unit_item else ""
                num_points = num_points_item.text() if num_points_item else ""
                min_val = min_item.text() if min_item else ""
                max_val = max_item.text() if max_item else ""
                mean_val = mean_item.text() if mean_item else ""
                std_dev_val = std_dev_item.text() if std_dev_item else ""
                
                # Add row data
                table_rows.append({
                    'device_id': device_id,
                    'data_type': data_type,
                    'latest_value': latest_value,
                    'unit': unit,
                    'number_of_points': num_points,
                    'min': min_val,
                    'max': max_val,
                    'mean': mean_val,
                    'std_dev': std_dev_val
                })
            
            if not table_rows:
                QMessageBox.warning(self, "No Data", "No selected rows found in the table.")
                return
            
            # Write to CSV file
            csv_path = Path(file_path)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header (matching table columns, excluding "Select")
                writer.writerow([
                    'Device ID', 
                    'Data Type', 
                    'Latest Value', 
                    'Unit', 
                    'Number of Points', 
                    'Min', 
                    'Max', 
                    'Mean', 
                    'Std Dev'
                ])
                
                # Write data rows
                for row_data in table_rows:
                    writer.writerow([
                        row_data['device_id'],
                        row_data['data_type'],
                        row_data['latest_value'],
                        row_data['unit'],
                        row_data['number_of_points'],
                        row_data['min'],
                        row_data['max'],
                        row_data['mean'],
                        row_data['std_dev']
                    ])
            
            # Show success message
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {len(table_rows)} data series to:\n{file_path}"
            )
            
            self.logger.info(f"Exported {len(table_rows)} table rows to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Export Error", f"Error exporting to CSV: {str(e)}")
    
    def debug_data_state(self):
        """Debug method to show current data state"""
        if not self.data_manager:
            self.logger.debug("No data_manager available")
            return
        
        self.logger.debug("=== DATA STATE DEBUG ===")
        all_streams = self.data_manager.get_all_data_streams()
        self.logger.debug(f"Total devices: {len(all_streams)}")
        
        for device_id, device_streams in all_streams.items():
            self.logger.debug(f"Device: {device_id}")
            for data_type, stream in device_streams.items():
                latest_point = stream.get_latest_data_point()
                if latest_point:
                    self.logger.debug(f"  - {data_type}: {latest_point.value} ({latest_point.unit}) at {latest_point.timestamp}")
                else:
                    self.logger.debug(f"  - {data_type}: No data points")
        
        self.logger.debug(f"Selected series: {list(self.selected_series)}")
        self.logger.debug("=== END DEBUG ===")
    
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
            self.logger.debug("No new latest data detected, skipping data table update")
            return
        
        # Store current data signature for next comparison
        self._last_latest_data_signature = current_data_signature
        self.logger.debug("New latest data detected, updating data table")
        
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
            self.logger.error(f"Error generating latest data signature: {e}")
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
                        
    def browse_csv_file(self):
        """Open file dialog to select CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.csv_file_path.setText(file_path)
            self.preview_csv_file(file_path)
    
    def preview_csv_file(self, file_path: str):
        """Preview CSV file content"""
        try:
            self.csv_preview_table.setRowCount(0)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                # Try to detect if file has headers
                sample = f.read(1024)
                f.seek(0)
                has_header = csv.Sniffer().has_header(sample)
                
                if has_header:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    # Show first 10 rows
                    preview_rows = min(10, len(rows))
                    self.csv_preview_table.setRowCount(preview_rows)
                    
                    for i, row in enumerate(rows[:preview_rows]):
                        device_id = row.get('device_id', '')
                        data_type = row.get('data_type', '')
                        value = row.get('value', '')
                        timestamp = row.get('timestamp', '')
                        unit = row.get('unit', '')
                        metadata = row.get('metadata', '')
                        
                        self.csv_preview_table.setItem(i, 0, QTableWidgetItem(device_id))
                        self.csv_preview_table.setItem(i, 1, QTableWidgetItem(data_type))
                        self.csv_preview_table.setItem(i, 2, QTableWidgetItem(str(value)))
                        self.csv_preview_table.setItem(i, 3, QTableWidgetItem(timestamp))
                        self.csv_preview_table.setItem(i, 4, QTableWidgetItem(unit))
                        self.csv_preview_table.setItem(i, 5, QTableWidgetItem(metadata))
                    
                    self.csv_status_label.setText(f"Preview: {len(rows)} rows found in CSV file (with headers)")
                else:
                    # No headers, assume order
                    reader = csv.reader(f)
                    rows = list(reader)
                    
                    # Show first 10 rows
                    preview_rows = min(10, len(rows))
                    self.csv_preview_table.setRowCount(preview_rows)
                    
                    for i, row in enumerate(rows[:preview_rows]):
                        device_id = row[0] if len(row) > 0 else ''
                        data_type = row[1] if len(row) > 1 else ''
                        value = row[2] if len(row) > 2 else ''
                        timestamp = row[3] if len(row) > 3 else ''
                        unit = row[4] if len(row) > 4 else ''
                        metadata = row[5] if len(row) > 5 else ''
                        
                        self.csv_preview_table.setItem(i, 0, QTableWidgetItem(device_id))
                        self.csv_preview_table.setItem(i, 1, QTableWidgetItem(data_type))
                        self.csv_preview_table.setItem(i, 2, QTableWidgetItem(str(value)))
                        self.csv_preview_table.setItem(i, 3, QTableWidgetItem(timestamp))
                        self.csv_preview_table.setItem(i, 4, QTableWidgetItem(unit))
                        self.csv_preview_table.setItem(i, 5, QTableWidgetItem(metadata))
                    
                    self.csv_status_label.setText(f"Preview: {len(rows)} rows found in CSV file (no headers, using column order)")
            
        except Exception as e:
            self.logger.error(f"Error previewing CSV file: {e}")
            QMessageBox.warning(self, "Preview Error", f"Error previewing CSV file: {str(e)}")
            self.csv_status_label.setText(f"Error: {str(e)}")
    
    def load_csv_data(self):
        """Load CSV data into DataManager"""
        file_path = self.csv_file_path.text().strip()
        
        if not file_path:
            QMessageBox.warning(self, "No File Selected", "Please select a CSV file first")
            return
        
        # Ask user if they want to clear existing data
        if self.data_manager and self.data_manager.data_streams:
            reply = QMessageBox.question(
                self,
                "Clear Existing Data?",
                "Loading CSV will clear all existing data in DataManager.\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        if not self.data_manager:
            # Create a new DataManager if not connected to API
            from data_manager import DataManager
            self.data_manager = DataManager()
            self.logger.info("Created new DataManager for CSV data")
        else:
            # Clear existing data streams before loading new data
            self.logger.info("Clearing existing data from DataManager")
            self.data_manager.data_streams.clear()
        
        # Clear chart and selected series
        if self.historical_chart:
            self.historical_chart.clear_all_series()
        self.selected_series.clear()
        
        # Uncheck all checkboxes in device data table
        if self.device_data_table:
            for row in range(self.device_data_table.rowCount()):
                checkbox = self.device_data_table.cellWidget(row, 5)
                if checkbox:
                    checkbox.setChecked(False)
        
        try:
            loaded_data = self.parse_csv_file(file_path)
            
            if not loaded_data:
                QMessageBox.warning(self, "Load Error", "No valid data found in CSV file")
                return
            
            # Process data using DataManager
            processed_count = 0
            error_count = 0
            
            for device_id, device_data in loaded_data.items():
                for data_type, data_points in device_data.items():
                    for data_point_dict in data_points:
                        try:
                            # Create DataPoint
                            from data_manager import DataPoint
                            data_point = DataPoint(
                                value=data_point_dict["value"],
                                timestamp=data_point_dict["timestamp"],
                                unit=data_point_dict.get("unit", ""),
                                metadata=data_point_dict.get("metadata", {})
                            )
                            
                            # Get or create data stream
                            if device_id not in self.data_manager.data_streams:
                                self.data_manager.data_streams[device_id] = {}
                            
                            if data_type not in self.data_manager.data_streams[device_id]:
                                from data_manager import DataStream
                                self.data_manager.data_streams[device_id][data_type] = DataStream(device_id, data_type)
                            
                            # Add data point
                            stream = self.data_manager.data_streams[device_id][data_type]
                            stream.add_data_point(data_point)
                            processed_count += 1
                            
                        except Exception as e:
                            self.logger.error(f"Error processing data point: {e}")
                            error_count += 1
                            continue
            
            # Update statistics
            stats_text = f"CSV Load Complete!\n"
            stats_text += f"Processed: {processed_count} data points\n"
            stats_text += f"Errors: {error_count}\n"
            stats_text += f"Devices: {len(loaded_data)}\n"
            
            total_data_types = sum(len(device_data) for device_data in loaded_data.values())
            stats_text += f"Data Types: {total_data_types}"
            
            self.csv_stats_text.setPlainText(stats_text)
            self.csv_status_label.setText(f"Status: Successfully loaded {processed_count} data points")
            
            # Show success message
            QMessageBox.information(
                self,
                "CSV Load Complete",
                f"Successfully loaded {processed_count} data points from CSV file.\n"
                f"Errors: {error_count}\n\n"
                f"Data is now available in the Data Visualization tab."
            )
            
            # Refresh UI to show new data
            self.refresh_device_data()
            
        except Exception as e:
            self.logger.error(f"Error loading CSV file: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Load Error", f"Error loading CSV file: {str(e)}")
            self.csv_status_label.setText(f"Error: {str(e)}")
    
    def parse_csv_file(self, file_path: str) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Parse CSV file and return data in DataManager format"""
        loaded_data = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Try to detect if file has headers
                sample = f.read(1024)
                f.seek(0)
                has_header = csv.Sniffer().has_header(sample)
                
                reader = csv.DictReader(f) if has_header else csv.reader(f)
                
                if has_header:
                    # Process with headers
                    for row_num, row in enumerate(reader, start=2):
                        try:
                            device_id = row.get('device_id', '').strip()
                            data_type = row.get('data_type', '').strip()
                            value_str = row.get('value', '').strip()
                            timestamp_str = row.get('timestamp', '').strip()
                            unit = row.get('unit', '').strip()
                            metadata_str = row.get('metadata', '').strip()
                            
                            if not device_id or not data_type or not value_str or not timestamp_str:
                                self.logger.warning(f"Skipping row {row_num}: missing required fields")
                                continue
                            
                            # Parse value (try numeric first, then string)
                            try:
                                if '.' in value_str:
                                    value = float(value_str)
                                else:
                                    value = int(value_str)
                            except ValueError:
                                value = value_str
                            
                            # Parse timestamp
                            timestamp = self.parse_timestamp(timestamp_str)
                            if not timestamp:
                                self.logger.warning(f"Skipping row {row_num}: invalid timestamp format")
                                continue
                            
                            # Parse metadata (JSON string if provided)
                            metadata = {}
                            if metadata_str:
                                try:
                                    metadata = json.loads(metadata_str)
                                except json.JSONDecodeError:
                                    metadata = {"raw": metadata_str}
                            
                            # Organize by device_id and data_type
                            if device_id not in loaded_data:
                                loaded_data[device_id] = {}
                            
                            if data_type not in loaded_data[device_id]:
                                loaded_data[device_id][data_type] = []
                            
                            loaded_data[device_id][data_type].append({
                                "value": value,
                                "timestamp": timestamp,
                                "unit": unit,
                                "metadata": metadata
                            })
                            
                        except Exception as e:
                            self.logger.error(f"Error parsing row {row_num}: {e}")
                            continue
                
                else:
                    # Process without headers (assume order: device_id, data_type, value, timestamp, unit, metadata)
                    for row_num, row in enumerate(reader, start=1):
                        try:
                            if len(row) < 4:
                                self.logger.warning(f"Skipping row {row_num}: insufficient columns")
                                continue
                            
                            device_id = row[0].strip()
                            data_type = row[1].strip()
                            value_str = row[2].strip()
                            timestamp_str = row[3].strip()
                            unit = row[4].strip() if len(row) > 4 else ""
                            metadata_str = row[5].strip() if len(row) > 5 else ""
                            
                            if not device_id or not data_type or not value_str or not timestamp_str:
                                continue
                            
                            # Parse value
                            try:
                                if '.' in value_str:
                                    value = float(value_str)
                                else:
                                    value = int(value_str)
                            except ValueError:
                                value = value_str
                            
                            # Parse timestamp
                            timestamp = self.parse_timestamp(timestamp_str)
                            if not timestamp:
                                continue
                            
                            # Parse metadata
                            metadata = {}
                            if metadata_str:
                                try:
                                    metadata = json.loads(metadata_str)
                                except json.JSONDecodeError:
                                    metadata = {"raw": metadata_str}
                            
                            # Organize by device_id and data_type
                            if device_id not in loaded_data:
                                loaded_data[device_id] = {}
                            
                            if data_type not in loaded_data[device_id]:
                                loaded_data[device_id][data_type] = []
                            
                            loaded_data[device_id][data_type].append({
                                "value": value,
                                "timestamp": timestamp,
                                "unit": unit,
                                "metadata": metadata
                            })
                            
                        except Exception as e:
                            self.logger.error(f"Error parsing row {row_num}: {e}")
                            continue
        
        except Exception as e:
            self.logger.error(f"Error reading CSV file: {e}")
            raise
        
        return loaded_data
    
    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from string (ISO format or Unix timestamp)"""
        try:
            # Try ISO format first
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try Unix timestamp (seconds)
                timestamp_float = float(timestamp_str)
                if timestamp_float < 1e10:  # Seconds
                    return datetime.fromtimestamp(timestamp_float)
                else:  # Milliseconds
                    return datetime.fromtimestamp(timestamp_float / 1000.0)
            except (ValueError, OSError):
                # Try common formats
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S.%f",
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(timestamp_str, fmt)
                    except ValueError:
                        continue
                return None
    
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Device Emulator Qt API Client")
    parser.add_argument('-l', '--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       default='ERROR',
                       help='Set the logging level (default: ERROR)')
    
    args = parser.parse_args()
    
    # Convert string to logging level
    log_level = getattr(logging, args.log_level.upper())
    
    # Setup logging
    logging.basicConfig(
        level=log_level,
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
