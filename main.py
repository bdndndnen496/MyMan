from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
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
client_settings = {}
admin_ws = None

@app.get("/clients")
async def list_clients():
    return {"clients": list(clients.keys())}

@app.websocket("/ws/client/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    client_settings[client_id] = {"quality": 50, "sleep": 0.03}
    try:
        while True:
            data = await websocket.receive()
            if "text" in data:
                msg = data["text"]
                if admin_ws:
                    await admin_ws.send_text(f"[{client_id}] {msg}")
            elif "bytes" in data:
                if admin_ws:
                    await admin_ws.send_bytes(data["bytes"])
    except WebSocketDisconnect:
        clients.pop(client_id, None)
        client_settings.pop(client_id, None)

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
            if msg.get("quality") is not None:
                client_settings[target]["quality"] = msg["quality"]
                await clients[target].send_text(f"set_quality:{msg['quality']}")
            if msg.get("sleep") is not None:
                client_settings[target]["sleep"] = msg["sleep"]
                await clients[target].send_text(f"set_sleep:{msg['sleep']}")
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
