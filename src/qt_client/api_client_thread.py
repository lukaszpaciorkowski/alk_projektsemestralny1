#!/usr/bin/env python3
"""
Centralized API client thread for managing all API requests
"""

import asyncio
import aiohttp
import logging
import queue
import threading
import time
from typing import Dict, Any, Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal
import sys
# Import handling for both package and direct execution
try:
    from .data_manager import DataManager
except ImportError:
    # Fallback for direct execution
    from data_manager import DataManager


class ApiClientThread(QThread):
    """Centralized thread for making API calls without blocking the UI"""
    
    # Signals for different types of responses
    response_received = pyqtSignal(dict, str)  # response_data, endpoint
    error_occurred = pyqtSignal(str, str)  # error_message, endpoint
    health_check_passed = pyqtSignal()  # health check successful
    health_check_failed = pyqtSignal(str)  # health check failed with error
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        super().__init__()
        # logging.basicConfig(
        # level=logging.DEBUG,
        # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        #     handlers=[
        #         logging.StreamHandler(sys.stdout),  # Console output
        #         logging.FileHandler('qt_client.log', mode='w')  # File output
        #     ]
        # )
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.loop = None
        self.logger = logging.getLogger(f"{__name__}.ApiClientThread")
        
        self.is_running = False
        self.request_queue = queue.Queue()
        self.shutdown_event = threading.Event()
        
        # Create DataManager instance for centralized data storage
        self.data_manager = DataManager()
        
        # Scheduled data fetching
        self.data_fetch_interval = 10000  # 10 seconds default
        self.is_data_fetching = False
        self.data_fetch_in_progress = False
        self.timer_task = None
        
        # Startup synchronization
        self.startup_event = threading.Event()
        self.startup_complete = False
        
    def run(self):
        """Setup async session and process requests from queue"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.is_running = True
        
        try:
            # Create session in the event loop
            self.loop.run_until_complete(self._create_session())
            self.logger.debug("API client thread started successfully")
            
            # Signal that startup is complete
            self.startup_complete = True
            self.startup_event.set()
            
            # Start the event loop running
            self.loop.run_until_complete(self._run_event_loop())
                    
        except Exception as e:
            self.logger.error(f"Error in API client thread: {e}")
        finally:
            # Cleanup
            self.is_running = False
            if self.session:
                try:
                    self.loop.run_until_complete(self.session.close())
                except Exception as e:
                    self.logger.error(f"Error closing session: {e}")
            self.loop.close()
            self.logger.debug("API client thread stopped")
    
    async def _run_event_loop(self):
        """Run the main event loop for processing requests"""
        last_data_fetch = 0
        
        try:
            while not self.shutdown_event.is_set():
                current_time = time.time()
                
                # Check for scheduled data fetching
                if (self.is_data_fetching and 
                    not self.data_fetch_in_progress and 
                    current_time - last_data_fetch >= self.data_fetch_interval / 1000.0):
                    
                    self.logger.debug("Triggering scheduled data fetch")
                    await self._make_data_request_async()
                    last_data_fetch = current_time
                
                try:
                    # Get request from queue with timeout
                    request = self.request_queue.get(timeout=0.1)
                    if request is None:  # Shutdown signal
                        break
                    
                    # Process the request
                    await self._handle_request(request)
                    self.request_queue.task_done()
                    
                except queue.Empty:
                    # No requests, yield control
                    await asyncio.sleep(0.01)
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in event loop: {e}")
        finally:
            # Cancel timer task if it exists
            if self.timer_task and not self.timer_task.done():
                self.timer_task.cancel()
                try:
                    await self.timer_task
                except asyncio.CancelledError:
                    pass
    
    async def _create_session(self):
        """Create the aiohttp session"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        )
        self.logger.debug("aiohttp session created")
    
    async def _handle_request(self, request: Dict[str, Any]):
        """Handle a single request"""
        try:
            endpoint = request["endpoint"]
            method = request.get("method", "GET")
            params = request.get("params")
            callback = request.get("callback")
            
            self.logger.debug(f"Handling request to {endpoint}")
            
            # Track data fetch progress
            if endpoint == "/data":
                self.data_fetch_in_progress = True
            
            if not self.session:
                self.logger.error("Session not available - thread may not be running")
                self.error_occurred.emit("Session not available", endpoint)
                if endpoint == "/data":
                    self.data_fetch_in_progress = False
                return
            
            url = f"{self.base_url}{endpoint}"
            self.logger.debug(f"Request URL: {url}")
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            if method.upper() == "GET":
                async with self.session.get(url, params=params, timeout=timeout) as response:
                    self.logger.debug(f"Response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        self.logger.debug(f"Response data received for {endpoint}")
                        self.response_received.emit(data, endpoint)
                        
                        # Special handling for specific endpoints
                        if endpoint == "/data":
                            self.data_fetch_in_progress = False
                            # Store data in DataManager instead of emitting signal
                            self.data_manager.process_data_batch(data)
                        elif endpoint == "/health":
                            self.health_check_passed.emit()
                        
                        # Call custom callback if provided
                        if callback:
                            callback(data, endpoint)
                    else:
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        self.logger.error(f"HTTP error: {error_msg}")
                        self.error_occurred.emit(error_msg, endpoint)
                        
                        if endpoint == "/data":
                            self.data_fetch_in_progress = False
                        elif endpoint == "/health":
                            self.health_check_failed.emit(error_msg)
            else:
                async with self.session.post(url, json=params, timeout=timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.response_received.emit(data, endpoint)
                        
                        if callback:
                            callback(data, endpoint)
                    else:
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        self.error_occurred.emit(error_msg, endpoint)
                        
        except asyncio.TimeoutError:
            error_msg = f"Request timeout for {request['endpoint']}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg, request["endpoint"])
            if request["endpoint"] == "/data":
                self.data_fetch_in_progress = False
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error in _handle_request for {request['endpoint']}: {e}")
            self.error_occurred.emit(error_msg, request["endpoint"])
            
            if request["endpoint"] == "/data":
                self.data_fetch_in_progress = False
            elif request["endpoint"] == "/health":
                self.health_check_failed.emit(error_msg)
    
    def make_request(self, endpoint: str, method: str = "GET", params: Dict[str, Any] = None, 
                    callback: Optional[Callable] = None):
        """Make an API request (synchronous interface)"""
        self.logger.debug(f"Making request to {endpoint} with method {method}")
        
        if not self.is_running:
            self.logger.error("Thread not running")
            self.error_occurred.emit("Thread not running", endpoint)
            return
        
        if self.shutdown_event.is_set():
            self.logger.error("Thread is shutting down")
            self.error_occurred.emit("Thread is shutting down", endpoint)
            return
        
        # Queue the request
        request = {
            "endpoint": endpoint,
            "method": method,
            "params": params,
            "callback": callback
        }
        try:
            self.request_queue.put(request)
            self.logger.debug(f"Request queued successfully for {endpoint}")
        except Exception as e:
            self.logger.error(f"Error queuing request: {e}")
            self.error_occurred.emit(f"Error queuing request: {e}", endpoint)
    
    def make_data_request(self, callback: Optional[Callable] = None):
        """Make a request to the /data endpoint"""
        if self.data_fetch_in_progress:
            self.logger.debug("Data fetch already in progress, skipping request")
            return
        self.make_request("/data", "GET", callback=callback)
    
    def make_health_check(self, callback: Optional[Callable] = None):
        """Make a health check request"""
        self.make_request("/health", "GET", callback=callback)
    
    def make_devices_request(self, callback: Optional[Callable] = None):
        """Make a request to get devices"""
        self.make_request("/devices", "GET", callback=callback)
    
    def make_device_request(self, device_id: str, callback: Optional[Callable] = None):
        """Make a request for specific device data"""
        self.make_request(f"/devices/{device_id}", "GET", callback=callback)
    
    def make_device_data_request(self, device_id: str, callback: Optional[Callable] = None):
        """Make a request for specific device data"""
        self.make_request(f"/data/{device_id}", "GET", callback=callback)
    
    def make_specific_data_request(self, device_id: str, data_type: str, callback: Optional[Callable] = None):
        """Make a request for specific device data type"""
        self.make_request(f"/data/{device_id}/{data_type}", "GET", callback=callback)
    
    def make_stop_request(self, callback: Optional[Callable] = None):
        """Make a request to stop the emulator"""
        self.make_request("/stop", "GET", callback=callback)
    
    def make_api_docs_request(self, callback: Optional[Callable] = None):
        """Make a request for API documentation"""
        self.make_request("/api", "GET", callback=callback)
    
    def start_scheduled_data_fetching(self, interval_ms: int = 10000):
        """Start scheduled data fetching"""
        if self.is_data_fetching:
            self.logger.warning("Scheduled data fetching already running")
            return
            
        # Wait for startup to complete if not already done
        if not self.startup_complete:
            self.logger.debug("Waiting for API client thread startup to complete...")
            if not self.startup_event.wait(timeout=5.0):
                self.logger.error("Timeout waiting for API client thread startup")
                return
        
        if not self.is_running or not self.loop:
            self.logger.error("Cannot start scheduled data fetching: thread not running or loop not available")
            return
            
        self.data_fetch_interval = interval_ms
        self.is_data_fetching = True
        
        # Use a simple approach - just set the flag and let the event loop handle it
        self.logger.info(f"Started scheduled data fetching every {interval_ms}ms ({interval_ms/1000:.1f}s)")
    
    def stop_scheduled_data_fetching(self):
        """Stop scheduled data fetching"""
        if not self.is_data_fetching:
            return
            
        self.is_data_fetching = False
        self.data_fetch_in_progress = False
        self.logger.info("Stopped scheduled data fetching")
    
    def set_data_fetch_interval(self, interval_ms: int):
        """Set the data fetch interval"""
        self.data_fetch_interval = interval_ms
        # Restart with new interval if currently fetching
        if self.is_data_fetching:
            self.stop_scheduled_data_fetching()
            self.start_scheduled_data_fetching(interval_ms)
    
    
    async def _make_data_request_async(self):
        """Make a data request directly in async context (for scheduled fetching)"""
        try:
            if self.data_fetch_in_progress:
                self.logger.debug("Data fetch already in progress, skipping")
                return
                
            if not self.session:
                self.logger.warning("Session not available for data request")
                return
            
            self.data_fetch_in_progress = True
            self.logger.debug("Making scheduled data request to /data")
            
            url = f"{self.base_url}/data"
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            async with self.session.get(url, timeout=timeout) as response:
                self.logger.debug(f"Data response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug("Scheduled data request successful")
                    # Store data in DataManager
                    self.data_manager.process_data_batch(data)
                    # Emit response signal for UI
                    self.response_received.emit(data, "/data")
                else:
                    error_msg = f"HTTP {response.status}: {await response.text()}"
                    self.logger.error(f"Scheduled data request failed: {error_msg}")
                    self.error_occurred.emit(error_msg, "/data")
                    
        except asyncio.TimeoutError:
            error_msg = "Scheduled data request timeout"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg, "/data")
        except Exception as e:
            error_msg = f"Scheduled data request error: {str(e)}"
            self.logger.error(error_msg)
            self.error_occurred.emit(error_msg, "/data")
        finally:
            self.data_fetch_in_progress = False
    
    def get_session(self):
        """Get the aiohttp session (for use by other components)"""
        return self.session
    
    def get_loop(self):
        """Get the asyncio event loop (for use by other components)"""
        return self.loop
    
    def get_data_manager(self):
        """Get the DataManager instance (for use by UI components)"""
        return self.data_manager
    
    def is_scheduled_fetching_active(self):
        """Check if scheduled data fetching is active"""
        return self.is_data_fetching and self.is_running and self.loop and self.loop.is_running()
    
    def wait_for_ready(self, timeout: float = 5.0):
        """Wait for the thread to be ready (session created)"""
        return self.startup_event.wait(timeout=timeout)
    
    def stop(self):
        """Stop the thread and cleanup"""
        self.logger.debug("Stopping API client thread...")
        self.is_running = False
        self.shutdown_event.set()
        
        # Stop scheduled data fetching
        self.stop_scheduled_data_fetching()
        
        # Reset startup state
        self.startup_complete = False
        self.startup_event.clear()
        
        # Send shutdown signal to queue
        try:
            self.request_queue.put(None)
        except Exception as e:
            self.logger.error(f"Error sending shutdown signal: {e}")
        
        # Wait for thread to finish
        self.quit()
        self.wait()
    
    def cleanup(self):
        """Cleanup method for proper shutdown"""
        self.logger.debug("Starting cleanup...")
        self.stop()
        self.logger.debug("Cleanup completed")
