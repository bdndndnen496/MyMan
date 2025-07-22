from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import asyncio
import os

app = FastAPI()

clients = {}
admin_ws = None

@app.websocket("/ws/client/{client_id}")
async def ws_client(ws: WebSocket, client_id: str):
    await ws.accept()
    clients[client_id] = ws
    try:
        while True:
            msg = await ws.receive()
            if "text" in msg:
                if admin_ws:
                    await admin_ws.send_text(f"[{client_id}] {msg['text']}")
            elif "bytes" in msg:
                if admin_ws:
                    await admin_ws.send_bytes(msg["bytes"])
    except WebSocketDisconnect:
        clients.pop(client_id, None)

@app.websocket("/ws/admin")
async def ws_admin(ws: WebSocket):
    global admin_ws
    await ws.accept()
    admin_ws = ws
    await ws.send_text(json.dumps({
        "type": "init",
        "clients": list(clients.keys())
    }))
    try:
        while True:
            msg = await ws.receive_json()
            target = msg.get("target")
            cmd = msg.get("cmd")
            if target in clients:
                await clients[target].send_text(cmd)
    except WebSocketDisconnect:
        admin_ws = None

@app.get("/")
async def index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
