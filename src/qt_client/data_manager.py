#!/usr/bin/env python3
"""
DataManager class for periodic data fetching and analysis
"""

import json
import logging
import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class DataPoint:
    """Represents a single data point with timestamp and metadata"""
    value: Any
    timestamp: datetime
    unit: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "unit": self.unit,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataPoint':
        """Create from dictionary"""
        return cls(
            value=data["value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            unit=data.get("unit", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class DataStream:
    """Represents a data stream for a specific device and data type"""
    device_id: str
    data_type: str
    data_points: deque = field(default_factory=lambda: deque(maxlen=1000))  # Keep last 1000 points
    last_update: Optional[datetime] = None
    
    def add_data_point(self, data_point: DataPoint):
        """Add a new data point to the stream"""
        self.data_points.append(data_point)
        self.last_update = data_point.timestamp
    
    def get_latest_value(self) -> Optional[Any]:
        """Get the latest value"""
        if self.data_points:
            return self.data_points[-1].value
        return None
    
    def get_latest_data_point(self) -> Optional[DataPoint]:
        """Get the latest data point"""
        if self.data_points:
            return self.data_points[-1]
        return None
    
    def get_values_in_range(self, start_time: datetime, end_time: datetime) -> List[Any]:
        """Get all values within a time range (optimized)"""
        # Since data_points is a deque, we can iterate efficiently
        # For small datasets, this is fine. For large datasets, consider binary search
        return [point.value for point in self.data_points 
                if start_time <= point.timestamp <= end_time]
    
    def get_data_points_in_range(self, start_time: datetime, end_time: datetime) -> List[DataPoint]:
        """Get all data points within a time range (optimized)"""
        # Since data_points is a deque, we can iterate efficiently
        return [point for point in self.data_points 
                if start_time <= point.timestamp <= end_time]


class DataAnalytics:
    """Analytics methods for data streams"""
    
    @staticmethod
    def calculate_average(stream: DataStream, time_window: Optional[timedelta] = None) -> Optional[float]:
        """Calculate average value over time window or all data"""
        if not stream.data_points:
            return None
        
        if time_window:
            end_time = datetime.now()
            start_time = end_time - time_window
            values = stream.get_values_in_range(start_time, end_time)
        else:
            values = [point.value for point in stream.data_points]
        
        # Filter numeric values
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if not numeric_values:
            return None
        
        return statistics.mean(numeric_values)
    
    @staticmethod
    def calculate_median(stream: DataStream, time_window: Optional[timedelta] = None) -> Optional[float]:
        """Calculate median value over time window or all data"""
        if not stream.data_points:
            return None
        
        if time_window:
            end_time = datetime.now()
            start_time = end_time - time_window
            values = stream.get_values_in_range(start_time, end_time)
        else:
            values = [point.value for point in stream.data_points]
        
        # Filter numeric values
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if not numeric_values:
            return None
        
        return statistics.median(numeric_values)
    
    @staticmethod
    def calculate_standard_deviation(stream: DataStream, time_window: Optional[timedelta] = None) -> Optional[float]:
        """Calculate standard deviation over time window or all data"""
        if not stream.data_points:
            return None
        
        if time_window:
            end_time = datetime.now()
            start_time = end_time - time_window
            values = stream.get_values_in_range(start_time, end_time)
        else:
            values = [point.value for point in stream.data_points]
        
        # Filter numeric values
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if len(numeric_values) < 2:
            return None
        
        return statistics.stdev(numeric_values)
    
    @staticmethod
    def calculate_trend(stream: DataStream, time_window: Optional[timedelta] = None) -> Optional[float]:
        """Calculate linear trend (slope) over time window or all data"""
        if not stream.data_points:
            return None
        
        if time_window:
            end_time = datetime.now()
            start_time = end_time - time_window
            points = stream.get_data_points_in_range(start_time, end_time)
        else:
            points = list(stream.data_points)
        
        if len(points) < 2:
            return None
        
        # Filter numeric values and convert timestamps to numeric
        numeric_points = []
        for point in points:
            if isinstance(point.value, (int, float)):
                timestamp_numeric = point.timestamp.timestamp()
                numeric_points.append((timestamp_numeric, point.value))
        
        if len(numeric_points) < 2:
            return None
        
        # Calculate linear regression slope
        x_values = [p[0] for p in numeric_points]
        y_values = [p[1] for p in numeric_points]
        
        n = len(numeric_points)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in numeric_points)
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope
        denominator = (n * sum_x2 - sum_x * sum_x)
        if denominator == 0:
            return None  # All x values are the same, no trend can be calculated
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope
    
    @staticmethod
    def calculate_min_max(stream: DataStream, time_window: Optional[timedelta] = None) -> Optional[Dict[str, float]]:
        """Calculate min and max values over time window or all data"""
        if not stream.data_points:
            return None
        
        if time_window:
            end_time = datetime.now()
            start_time = end_time - time_window
            values = stream.get_values_in_range(start_time, end_time)
        else:
            values = [point.value for point in stream.data_points]
        
        # Filter numeric values
        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if not numeric_values:
            return None
        
        return {
            "min": min(numeric_values),
            "max": max(numeric_values)
        }
    
    @staticmethod
    def detect_anomalies(stream: DataStream, threshold: float = 2.0, time_window: Optional[timedelta] = None) -> List[DataPoint]:
        """Detect anomalous data points using z-score method"""
        if not stream.data_points:
            return []
        
        if time_window:
            end_time = datetime.now()
            start_time = end_time - time_window
            points = stream.get_data_points_in_range(start_time, end_time)
        else:
            points = list(stream.data_points)
        
        # Filter numeric values
        numeric_points = [p for p in points if isinstance(p.value, (int, float))]
        if len(numeric_points) < 3:
            return []
        
        values = [p.value for p in numeric_points]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        
        if stdev == 0:
            return []
        
        # Find anomalies
        anomalies = []
        for point in numeric_points:
            z_score = abs((point.value - mean) / stdev)
            if z_score > threshold:
                anomalies.append(point)
        
        return anomalies


class DataManager:
    """Simple data storage and analytics class (no threading, no Qt signals)"""
    
    def __init__(self, data_updated_callback=None):
        self.logger = logging.getLogger(f"{__name__}.DataManager")
        
        # Data storage
        self.data_streams: Dict[str, Dict[str, DataStream]] = defaultdict(dict)
        
        # Optional callback for data updates
        self.data_updated_callback = data_updated_callback
        
    def process_data(self, data: Dict[str, Any]):
        """Process data received from API client (optimized to prevent hanging)"""
        self._process_fetched_data(data)
    
    def process_data_batch(self, data: Dict[str, Any]):
        """Process data in batch mode (simple, no signals)"""
        try:
            if "data" not in data:
                return
            
            processed_count = 0
            for device_id, device_data in data["data"].items():
                for data_type, data_point_dict in device_data.items():
                    try:
                        # Create DataPoint
                        data_point = DataPoint(
                            value=data_point_dict["value"],
                            timestamp=datetime.fromisoformat(data_point_dict["timestamp"]),
                            unit=data_point_dict.get("unit", ""),
                            metadata=data_point_dict.get("metadata", {})
                        )
                        
                        # Get or create data stream
                        if device_id not in self.data_streams:
                            self.data_streams[device_id] = {}
                        
                        if data_type not in self.data_streams[device_id]:
                            self.data_streams[device_id][data_type] = DataStream(device_id, data_type)
                        
                        # Add data point
                        stream = self.data_streams[device_id][data_type]
                        stream.add_data_point(data_point)
                        processed_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing data point for {device_id}.{data_type}: {e}")
                        continue
            
            self.logger.debug(f"Processed {processed_count} data points")
            
            # Call callback if provided
            if self.data_updated_callback and processed_count > 0:
                self.data_updated_callback("batch", "processed", {"count": processed_count})
                    
        except Exception as e:
            self.logger.error(f"Error processing batch data: {e}")
    
    def _process_fetched_data(self, data: Dict[str, Any]):
        """Process fetched data and update streams (simple, no signals)"""
        try:
            if "data" not in data:
                return
            
            for device_id, device_data in data["data"].items():
                for data_type, data_point_dict in device_data.items():
                    try:
                        # Create DataPoint
                        data_point = DataPoint(
                            value=data_point_dict["value"],
                            timestamp=datetime.fromisoformat(data_point_dict["timestamp"]),
                            unit=data_point_dict.get("unit", ""),
                            metadata=data_point_dict.get("metadata", {})
                        )
                        
                        # Get or create data stream
                        if device_id not in self.data_streams:
                            self.data_streams[device_id] = {}
                        
                        if data_type not in self.data_streams[device_id]:
                            self.data_streams[device_id][data_type] = DataStream(device_id, data_type)
                        
                        # Add data point
                        stream = self.data_streams[device_id][data_type]
                        stream.add_data_point(data_point)
                        
                        # No signals - simple data storage only
                        
                    except Exception as e:
                        self.logger.error(f"Error processing data point for {device_id}.{data_type}: {e}")
                        continue
        except Exception as e:
            self.logger.error(f"Error processing fetched data: {e}")
    
    def _calculate_analytics(self, stream: DataStream) -> Dict[str, Any]:
        """Calculate analytics for a data stream (optimized)"""
        try:
            analytics = {}
            
            # Basic statistics (always fast)
            analytics["latest_value"] = stream.get_latest_value()
            analytics["latest_timestamp"] = stream.last_update.isoformat() if stream.last_update else None
            analytics["data_point_count"] = len(stream.data_points)
            
            # Only calculate expensive analytics if we have enough data
            if len(stream.data_points) < 2:
                analytics["note"] = "Insufficient data for advanced analytics"
                return analytics
            
            # Time-based analytics (last 5 minutes) - only if we have recent data
            time_window = timedelta(minutes=5)
            recent_points = stream.get_data_points_in_range(
                datetime.now() - time_window, 
                datetime.now()
            )
            
            if len(recent_points) >= 2:
                analytics["average_5min"] = DataAnalytics.calculate_average(stream, time_window)
                analytics["median_5min"] = DataAnalytics.calculate_median(stream, time_window)
                analytics["std_dev_5min"] = DataAnalytics.calculate_standard_deviation(stream, time_window)
                analytics["trend_5min"] = DataAnalytics.calculate_trend(stream, time_window)
                analytics["min_max_5min"] = DataAnalytics.calculate_min_max(stream, time_window)
            else:
                analytics["note_5min"] = "Insufficient recent data for 5-minute analytics"
            
            # Overall analytics - only if we have enough data
            if len(stream.data_points) >= 3:
                analytics["average_all"] = DataAnalytics.calculate_average(stream)
                analytics["median_all"] = DataAnalytics.calculate_median(stream)
                analytics["std_dev_all"] = DataAnalytics.calculate_standard_deviation(stream)
                analytics["trend_all"] = DataAnalytics.calculate_trend(stream)
                analytics["min_max_all"] = DataAnalytics.calculate_min_max(stream)
                
                # Anomaly detection - only for larger datasets
                if len(stream.data_points) >= 10:
                    analytics["anomalies"] = len(DataAnalytics.detect_anomalies(stream, time_window=time_window))
                else:
                    analytics["anomalies"] = 0
            else:
                analytics["note_all"] = "Insufficient data for overall analytics"
            
            return analytics
        except Exception as e:
            self.logger.error(f"Error calculating analytics for {stream.device_id}.{stream.data_type}: {e}")
            # Return basic analytics in case of error
            return {
                "latest_value": stream.get_latest_value(),
                "latest_timestamp": stream.last_update.isoformat() if stream.last_update else None,
                "data_point_count": len(stream.data_points),
                "error": str(e)
            }
    
    def get_data_stream(self, device_id: str, data_type: str) -> Optional[DataStream]:
        """Get a specific data stream"""
        return self.data_streams.get(device_id, {}).get(data_type)
    
    def get_all_data_streams(self) -> Dict[str, Dict[str, DataStream]]:
        """Get all data streams"""
        return dict(self.data_streams)
    
    def get_device_data_streams(self, device_id: str) -> Dict[str, DataStream]:
        """Get all data streams for a specific device"""
        return dict(self.data_streams.get(device_id, {}))
    
    def get_latest_data(self) -> Dict[str, Dict[str, Any]]:
        """Get latest data from all streams"""
        latest_data = {}
        for device_id, device_streams in self.data_streams.items():
            latest_data[device_id] = {}
            for data_type, stream in device_streams.items():
                latest_point = stream.get_latest_data_point()
                if latest_point:
                    latest_data[device_id][data_type] = latest_point.to_dict()
        return latest_data
    
    def get_analytics(self, device_id: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Get analytics for a specific data stream (on-demand calculation)"""
        stream = self.get_data_stream(device_id, data_type)
        if stream:
            return self._calculate_analytics(stream)
        return None
    
    def calculate_analytics_for_stream(self, device_id: str, data_type: str) -> Optional[Dict[str, Any]]:
        """Calculate analytics for a specific stream (on-demand, no signals)"""
        stream = self.get_data_stream(device_id, data_type)
        if stream:
            analytics = self._calculate_analytics(stream)
            return analytics
        return None
    
    def get_all_analytics(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get analytics for all data streams"""
        all_analytics = {}
        for device_id, device_streams in self.data_streams.items():
            all_analytics[device_id] = {}
            for data_type, stream in device_streams.items():
                all_analytics[device_id][data_type] = self._calculate_analytics(stream)
        return all_analytics
    
    def clear_data(self, device_id: Optional[str] = None, data_type: Optional[str] = None):
        """Clear data for specific device/type or all data"""
        if device_id is None:
            # Clear all data
            self.data_streams.clear()
        elif data_type is None:
            # Clear all data for device
            if device_id in self.data_streams:
                del self.data_streams[device_id]
        else:
            # Clear specific data stream
            if device_id in self.data_streams and data_type in self.data_streams[device_id]:
                del self.data_streams[device_id][data_type]
    
    def export_data(self, device_id: Optional[str] = None, data_type: Optional[str] = None) -> Dict[str, Any]:
        """Export data to dictionary format"""
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "data_streams": {}
        }
        
        for dev_id, device_streams in self.data_streams.items():
            if device_id is not None and dev_id != device_id:
                continue
            
            export_data["data_streams"][dev_id] = {}
            for dt_type, stream in device_streams.items():
                if data_type is not None and dt_type != data_type:
                    continue
                
                export_data["data_streams"][dev_id][dt_type] = {
                    "device_id": stream.device_id,
                    "data_type": stream.data_type,
                    "last_update": stream.last_update.isoformat() if stream.last_update else None,
                    "data_points": [point.to_dict() for point in stream.data_points]
                }
        
        return export_data
    
    def import_data(self, data: Dict[str, Any]):
        """Import data from dictionary format"""
        if "data_streams" not in data:
            return
        
        for device_id, device_streams in data["data_streams"].items():
            for data_type, stream_data in device_streams.items():
                # Create or get stream
                if device_id not in self.data_streams:
                    self.data_streams[device_id] = {}
                
                if data_type not in self.data_streams[device_id]:
                    self.data_streams[device_id][data_type] = DataStream(device_id, data_type)
                
                stream = self.data_streams[device_id][data_type]
                
                # Import data points
                for point_data in stream_data.get("data_points", []):
                    data_point = DataPoint.from_dict(point_data)
                    stream.add_data_point(data_point)
    
