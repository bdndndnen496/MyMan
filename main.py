import asyncio
import websockets
import json
import uuid
import time
import os
from datetime import datetime
from typing import Dict, Set
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RemoteServer:
    def __init__(self):
        self.clients: Dict[str, dict] = {}  # client_id -> client_info
        self.controllers: Set[WebSocket] = set()  # web controllers
        self.sessions: Dict[str, str] = {}  # session_id -> client_id
        
    async def register_client(self, websocket: WebSocket, client_info):
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
        await websocket.send_text(json.dumps({
            'type': 'session_assigned',
            'session_id': session_id
        }))
        
        # Notify all controllers about new client
        await self.broadcast_client_list()
        
        logger.info(f"Client registered: {client_id} ({session_id})")
        return client_id
    
    async def register_controller(self, websocket: WebSocket):
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
    
    async def unregister_controller(self, websocket: WebSocket):
        """Unregister a web controller"""
        self.controllers.discard(websocket)
        logger.info("Controller unregistered")
    
    def generate_session_id(self):
        """Generate a unique 9-digit session ID"""
        import random
        return str(random.randint(100000000, 999999999))
    
    async def send_client_list(self, websocket: WebSocket):
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
            
            await websocket.send_text(json.dumps({
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
            except Exception as e:
                logger.error(f"Error broadcasting to controller: {e}")
                disconnected_controllers.add(controller)
        
        # Remove disconnected controllers
        for controller in disconnected_controllers:
            self.controllers.discard(controller)
    
    async def handle_client_message(self, websocket: WebSocket, client_id, data):
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
    
    async def handle_controller_message(self, websocket: WebSocket, data):
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
                        
                        await client_ws.send_text(json.dumps(control_data))
            
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
                await controller.send_text(json.dumps(data))
            except Exception as e:
                logger.error(f"Error broadcasting to controller: {e}")
                disconnected_controllers.add(controller)
        
        # Remove disconnected controllers
        for controller in disconnected_controllers:
            self.controllers.discard(controller)

# Global server instance
server = RemoteServer()

# FastAPI app
app = FastAPI(title="Remote Access Server")

# Create static directory if it doesn't exist
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

# Create index.html if it doesn't exist
index_path = static_dir / "index.html"
if not index_path.exists():
    # Create a basic index.html
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Remote Access Control</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Remote Access Control Panel</h1>
    <p>WebSocket server is running. Please upload the complete index.html file to the static directory.</p>
    <script>
        // Basic WebSocket connection test
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = protocol + '//' + window.location.host + '/ws/controller/';
        console.log('Attempting to connect to:', wsUrl);
        
        const ws = new WebSocket(wsUrl);
        ws.onopen = () => console.log('WebSocket connected');
        ws.onclose = () => console.log('WebSocket disconnected');
        ws.onerror = (error) => console.error('WebSocket error:', error);
    </script>
</body>
</html>""")

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    """Serve the main page"""
    try:
        with open(static_dir / "index.html", 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <body>
                <h1>Remote Access Server</h1>
                <p>Server is running, but index.html not found in static directory.</p>
                <p>Please upload the web interface files to the static directory.</p>
            </body>
        </html>
        """)

@app.websocket("/ws/client/")
async def websocket_client_endpoint(websocket: WebSocket):
    """WebSocket endpoint for clients"""
    await websocket.accept()
    client_id = None
    
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
                
                if data.get('type') == 'client_info' and not client_id:
                    # Register new client
                    client_id = await server.register_client(websocket, data)
                elif client_id:
                    # Handle client message
                    await server.handle_client_message(websocket, client_id, data)
                    
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from client")
            except Exception as e:
                logger.error(f"Error processing client message: {e}")
                
    except WebSocketDisconnect:
        logger.info("Client WebSocket disconnected")
    except Exception as e:
        logger.error(f"Client WebSocket error: {e}")
    finally:
        # Cleanup
        if client_id:
            await server.unregister_client(client_id)

@app.websocket("/ws/controller/")
async def websocket_controller_endpoint(websocket: WebSocket):
    """WebSocket endpoint for web controllers"""
    await websocket.accept()
    
    try:
        await server.register_controller(websocket)
        
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
                await server.handle_controller_message(websocket, data)
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from controller")
            except Exception as e:
                logger.error(f"Error processing controller message: {e}")
                
    except WebSocketDisconnect:
        logger.info("Controller WebSocket disconnected")
    except Exception as e:
        logger.error(f"Controller WebSocket error: {e}")
    finally:
        # Cleanup
        await server.unregister_controller(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {
        "status": "healthy",
        "clients_connected": len(server.clients),
        "controllers_connected": len(server.controllers)
    }

# For Render.com deployment
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)