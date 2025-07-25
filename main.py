import asyncio
import websockets
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Set
import logging
from pathlib import Path
import threading
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RemoteServer:
    def __init__(self):
        self.clients: Dict[str, dict] = {}  # client_id -> client_info
        self.controllers: Set[websockets.WebSocketServerProtocol] = set()  # web controllers
        self.sessions: Dict[str, str] = {}  # session_id -> client_id
        
    async def register_client(self, websocket, client_info):
        """Register a new client"""
        client_id = str(uuid.uuid4())
        session_id = self.generate_session_id()
        
        self.clients[client_id] = {
            'websocket': websocket,
            'session_id': session_id,
            'username': client_info.get('username', 'Unknown'),
            'ip': client_info.get('ip', 'Unknown'),
            'os': client_info.get('os', 'Unknown'),
            'hostname': client_info.get('hostname', 'Unknown'),
            'specs': client_info.get('specs', {}),
            'status': 'online',
            'connected_at': datetime.now().isoformat(),
            'last_seen': time.time()
        }
        
        self.sessions[session_id] = client_id
        
        # Send session ID to client
        await websocket.send(json.dumps({
            'type': 'session_assigned',
            'session_id': session_id
        }))
        
        # Notify all controllers about new client
        await self.broadcast_client_list()
        
        logger.info(f"Client registered: {client_id} ({session_id})")
        return client_id
    
    async def register_controller(self, websocket):
        """Register a web controller"""
        self.controllers.add(websocket)
        
        # Send current client list
        await self.send_client_list(websocket)
        
        logger.info("Controller registered")
    
    async def unregister_client(self, client_id):
        """Unregister a client"""
        if client_id in self.clients:
            session_id = self.clients[client_id]['session_id']
            del self.clients[client_id]
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            # Notify controllers
            await self.broadcast_client_list()
            logger.info(f"Client unregistered: {client_id}")
    
    async def unregister_controller(self, websocket):
        """Unregister a web controller"""
        self.controllers.discard(websocket)
        logger.info("Controller unregistered")
    
    def generate_session_id(self):
        """Generate a unique 9-digit session ID"""
        import random
        return str(random.randint(100000000, 999999999))
    
    async def send_client_list(self, websocket):
        """Send client list to a specific controller"""
        try:
            client_list = []
            for client_id, client_info in self.clients.items():
                client_list.append({
                    'client_id': client_id,
                    'session_id': client_info['session_id'],
                    'username': client_info['username'],
                    'ip': client_info['ip'],
                    'os': client_info['os'],
                    'hostname': client_info['hostname'],
                    'status': client_info['status'],
                    'connected_at': client_info['connected_at'],
                    'specs': client_info['specs']
                })
            
            await websocket.send(json.dumps({
                'type': 'client_list',
                'clients': client_list
            }))
        except Exception as e:
            logger.error(f"Error sending client list: {e}")
    
    async def broadcast_client_list(self):
        """Broadcast client list to all controllers"""
        if not self.controllers:
            return
        
        disconnected_controllers = set()
        
        for controller in self.controllers.copy():
            try:
                await self.send_client_list(controller)
            except websockets.exceptions.ConnectionClosed:
                disconnected_controllers.add(controller)
            except Exception as e:
                logger.error(f"Error broadcasting to controller: {e}")
                disconnected_controllers.add(controller)
        
        # Remove disconnected controllers
        for controller in disconnected_controllers:
            self.controllers.discard(controller)
    
    async def handle_client_message(self, websocket, client_id, data):
        """Handle message from client"""
        try:
            # Update last seen
            if client_id in self.clients:
                self.clients[client_id]['last_seen'] = time.time()
            
            message_type = data.get('type')
            
            if message_type in ['screen_frame', 'cmd_result', 'process_list', 'process_killed']:
                # Forward to controllers
                await self.broadcast_to_controllers(data)
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
    
    async def handle_controller_message(self, websocket, data):
        """Handle message from web controller"""
        try:
            message_type = data.get('type')
            
            if message_type == 'control_client':
                session_id = data.get('session_id')
                action = data.get('action')
                
                if session_id in self.sessions:
                    client_id = self.sessions[session_id]
                    if client_id in self.clients:
                        client_ws = self.clients[client_id]['websocket']
                        
                        # Forward control message to client
                        control_data = {
                            'type': action,
                            **{k: v for k, v in data.items() if k not in ['type', 'session_id']}
                        }
                        
                        await client_ws.send(json.dumps(control_data))
            
            elif message_type == 'get_client_list':
                await self.send_client_list(websocket)
                
        except Exception as e:
            logger.error(f"Error handling controller message: {e}")
    
    async def broadcast_to_controllers(self, data):
        """Broadcast data to all controllers"""
        if not self.controllers:
            return
        
        disconnected_controllers = set()
        
        for controller in self.controllers.copy():
            try:
                await controller.send(json.dumps(data))
            except websockets.exceptions.ConnectionClosed:
                disconnected_controllers.add(controller)
            except Exception as e:
                logger.error(f"Error broadcasting to controller: {e}")
                disconnected_controllers.add(controller)
        
        # Remove disconnected controllers
        for controller in disconnected_controllers:
            self.controllers.discard(controller)
    
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connections"""
        client_id = None
        
        try:
            if path == '/ws/client/':
                # Client connection
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        if data.get('type') == 'client_info' and not client_id:
                            # Register new client
                            client_id = await self.register_client(websocket, data)
                        elif client_id:
                            # Handle client message
                            await self.handle_client_message(websocket, client_id, data)
                            
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
            
            elif path == '/ws/controller/':
                # Controller connection
                await self.register_controller(websocket)
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self.handle_controller_message(websocket, data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received from controller")
                    except Exception as e:
                        logger.error(f"Error processing controller message: {e}")
            
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup
            if client_id:
                await self.unregister_client(client_id)
            else:
                await self.unregister_controller(websocket)

# Global server instance
server = RemoteServer()

async def websocket_handler(websocket, path):
    """WebSocket handler function"""
    await server.handle_websocket(websocket, path)

def serve_static_files():
    """Serve static files"""
    import http.server
    import socketserver
    import threading
    from pathlib import Path
    
    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(Path(__file__).parent / "static"), **kwargs)
        
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
    
    # Create static directory if it doesn't exist
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    
    PORT = 8000
    with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
        logger.info(f"Serving static files at http://localhost:{PORT}")
        httpd.serve_forever()

async def main():
    # Start static file server in separate thread
    static_thread = threading.Thread(target=serve_static_files, daemon=True)
    static_thread.start()
    
    # Start WebSocket server
    logger.info("Starting WebSocket server on port 8765")
    
    start_server = websockets.serve(websocket_handler, "0.0.0.0", 8765)
    
    await start_server
    
    # Keep server running
    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped")