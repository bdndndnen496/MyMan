import os
import json
import time
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default123")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}  # client_id -> websocket
client_infos = {}  # client_id -> info
admins = set()

@app.get("/")
async def root():
    return HTMLResponse("Remote Server is running.")

@app.websocket("/ws/client/")
async def client_socket(ws: WebSocket):
    await ws.accept()
    client_id = str(uuid.uuid4())
    clients[client_id] = ws
    print(f"[Client Connected] {client_id}")

    try:
        while True:
            data = await ws.receive_text()
            message = json.loads(data)
            message["client_id"] = client_id

            if message["type"] == "client_info":
                client_infos[client_id] = message

            for admin_ws in admins:
                await admin_ws.send_text(json.dumps(message))
    except WebSocketDisconnect:
        print(f"[Client Disconnected] {client_id}")
    finally:
        clients.pop(client_id, None)
        client_infos.pop(client_id, None)

@app.websocket("/ws/admin/")
async def admin_socket(ws: WebSocket):
    await ws.accept()
    try:
        auth = await ws.receive_text()
        msg = json.loads(auth)
        if msg.get("type") != "auth" or msg.get("password") != ADMIN_PASSWORD:
            await ws.send_text(json.dumps({"type": "auth_failed"}))
            await ws.close()
            return

        await ws.send_text(json.dumps({"type": "auth_success"}))
        admins.add(ws)
        print("[Admin Connected]")

        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg["type"] == "command":
                target = msg.get("target")
                if target in clients:
                    await clients[target].send(json.dumps(msg["command"]))
    except WebSocketDisconnect:
        print("[Admin Disconnected]")
    finally:
        admins.discard(ws)
