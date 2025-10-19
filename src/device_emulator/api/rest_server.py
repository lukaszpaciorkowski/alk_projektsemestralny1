"""
REST API server for device emulator
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from aiohttp import web, web_request
from aiohttp.web import Response

from shared.models.device_data import DeviceData


class RestApiServer:
    """REST API server for exposing device data"""
    
    def __init__(self, emulator, host: str = "localhost", port: int = 8080):
        self.emulator = emulator
        self.host = host
        self.port = port
        self.app = web.Application()
        self.logger = logging.getLogger(f"{__name__}.{host}:{port}")
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup REST API routes"""
        
        # Health check endpoint
        self.app.router.add_get('/health', self._health_check)
        
        # Device information endpoints
        self.app.router.add_get('/devices', self._get_all_devices)
        self.app.router.add_get('/devices/{device_id}', self._get_device_info)
        
        # Data endpoints
        self.app.router.add_get('/data', self._get_all_data)
        self.app.router.add_get('/data/{device_id}', self._get_device_data)
        self.app.router.add_get('/data/{device_id}/{data_type}', self._get_specific_data)
        
        # Real-time data endpoint (WebSocket)
        self.app.router.add_get('/ws', self._websocket_handler)
        
        # API documentation endpoint
        self.app.router.add_get('/api', self._api_documentation)
    
    async def _health_check(self, request: web_request.Request) -> Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "emulator": self.emulator.config.config_name if hasattr(self.emulator, 'config') else "Unknown"
        })
    
    async def _get_all_devices(self, request: web_request.Request) -> Response:
        """Get information about all devices"""
        try:
            if hasattr(self.emulator, 'get_all_devices_info'):
                devices_info = self.emulator.get_all_devices_info()
            else:
                # Fallback for basic emulator
                devices_info = {}
                for device_id in self.emulator.device_emulators.keys():
                    device_info = self.emulator.get_device_info(device_id)
                    if device_info:
                        devices_info[device_id] = device_info
            
            return web.json_response({
                "devices": devices_info,
                "count": len(devices_info),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Error getting devices: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_device_info(self, request: web_request.Request) -> Response:
        """Get information about a specific device"""
        try:
            device_id = request.match_info['device_id']
            
            if hasattr(self.emulator, 'get_device_info'):
                device_info = self.emulator.get_device_info(device_id)
            else:
                device_info = None
            
            if not device_info:
                return web.json_response({"error": f"Device {device_id} not found"}, status=404)
            
            return web.json_response({
                "device": device_info,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Error getting device info: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_all_data(self, request: web_request.Request) -> Response:
        """Get current data from all devices"""
        try:
            # Get latest data from the simplified emulator
            all_data = self.emulator.get_latest_data()
            
            # Convert to JSON-serializable format
            json_data = {}
            for device_id, device_data in all_data.items():
                json_data[device_id] = {}
                for data_type, data in device_data.items():
                    json_data[device_id][data_type] = {
                        "value": data.value,
                        "unit": data.unit,
                        "timestamp": data.timestamp.isoformat(),
                        "metadata": data.metadata
                    }
            
            return web.json_response({
                "data": json_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Error getting all data: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_device_data(self, request: web_request.Request) -> Response:
        """Get current data from a specific device"""
        try:
            device_id = request.match_info['device_id']
            
            # Get latest data for the device
            device_data = self.emulator.get_latest_data(device_id)
            
            if not device_data:
                return web.json_response({"error": f"Device {device_id} not found"}, status=404)
            
            # Convert to JSON-serializable format
            json_data = {}
            for data_type, data in device_data.items():
                json_data[data_type] = {
                    "value": data.value,
                    "unit": data.unit,
                    "timestamp": data.timestamp.isoformat(),
                    "metadata": data.metadata
                }
            
            return web.json_response({
                "device_id": device_id,
                "data": json_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Error getting device data: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_specific_data(self, request: web_request.Request) -> Response:
        """Get specific data type from a specific device"""
        try:
            device_id = request.match_info['device_id']
            data_type = request.match_info['data_type']
            
            # Get latest data for the specific data type
            specific_data = self.emulator.get_latest_data(device_id, data_type)
            
            if not specific_data:
                return web.json_response({"error": f"Data type {data_type} not found for device {device_id}"}, status=404)
            
            return web.json_response({
                "device_id": device_id,
                "data_type": data_type,
                "value": specific_data.value,
                "unit": specific_data.unit,
                "timestamp": specific_data.timestamp.isoformat(),
                "metadata": specific_data.metadata
            })
        except Exception as e:
            self.logger.error(f"Error getting specific data: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _websocket_handler(self, request: web_request.Request) -> web.WebSocketResponse:
        """WebSocket handler for real-time data"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.logger.info(f"WebSocket connection established from {request.remote}")
        
        try:
            while not ws.closed:
                # Generate fresh data
                if hasattr(self.emulator, 'generate_data_for_all_devices'):
                    all_data = await self.emulator.generate_data_for_all_devices()
                else:
                    # Fallback for basic emulator
                    all_data = {}
                    for device_id in self.emulator.device_emulators.keys():
                        device_data = {}
                        for data_type_name in self.emulator.device_emulators[device_id].get_available_data_types():
                            data = await self.emulator.device_emulators[device_id].generate_single_data(data_type_name)
                            if data:
                                device_data[data_type_name] = data
                        all_data[device_id] = device_data
                
                # Convert to JSON and send
                json_data = {}
                for device_id, device_data in all_data.items():
                    json_data[device_id] = {}
                    for data_type, data in device_data.items():
                        json_data[device_id][data_type] = {
                            "value": data.value,
                            "unit": data.unit,
                            "timestamp": data.timestamp.isoformat(),
                            "metadata": data.metadata
                        }
                
                await ws.send_str(json.dumps({
                    "type": "data_update",
                    "data": json_data,
                    "timestamp": datetime.now().isoformat()
                }))
                
                # Wait before next update
                await asyncio.sleep(1.0)
                
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
        finally:
            self.logger.info(f"WebSocket connection closed")
        
        return ws
    
    async def _api_documentation(self, request: web_request.Request) -> Response:
        """API documentation endpoint"""
        documentation = {
            "title": "Device Emulator REST API",
            "version": "1.0.0",
            "description": "REST API for accessing device emulator data",
            "endpoints": {
                "GET /health": "Health check endpoint",
                "GET /devices": "Get information about all devices",
                "GET /devices/{device_id}": "Get information about a specific device",
                "GET /data": "Get current data from all devices",
                "GET /data/{device_id}": "Get current data from a specific device",
                "GET /data/{device_id}/{data_type}": "Get specific data type from a specific device",
                "GET /ws": "WebSocket endpoint for real-time data",
                "GET /api": "This API documentation"
            },
            "examples": {
                "get_all_devices": "GET /devices",
                "get_device_info": "GET /devices/temp_sensor_001",
                "get_all_data": "GET /data",
                "get_device_data": "GET /data/temp_sensor_001",
                "get_temperature": "GET /data/temp_sensor_001/temperature"
            }
        }
        
        return web.json_response(documentation)
    
    async def start(self):
        """Start the REST API server"""
        self.logger.info(f"Starting REST API server on {self.host}:{self.port}")
        
        # Start the web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"REST API server started at http://{self.host}:{self.port}")
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.logger.info("REST API server stopped")
        finally:
            await runner.cleanup()
    
    async def stop(self):
        """Stop the REST API server"""
        self.logger.info("Stopping REST API server...")
