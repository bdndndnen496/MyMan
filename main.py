from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
