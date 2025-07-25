from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict, List
import json

app = FastAPI()

clients: Dict[str, WebSocket] = {}
admins: List[WebSocket] = []
PASSWORD = "supersecurepassword"

@app.websocket("/ws/client/{client_id}")
async def client_ws(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    for admin in admins:
        await admin.send_json({"type": "client_connected", "client_id": client_id})

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type")

            if msg_type in ("screen_frame", "cmd_result", "process_list"):
                for admin in admins:
                    await admin.send_text(data)
    except WebSocketDisconnect:
        clients.pop(client_id, None)
        for admin in admins:
            await admin.send_json({"type": "client_disconnected", "client_id": client_id})

@app.websocket("/ws/admin/")
async def admin_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        auth = await websocket.receive_text()
        data = json.loads(auth)
        if data.get("password") != PASSWORD:
            await websocket.send_json({"type": "auth_failed"})
            await websocket.close()
            return

        await websocket.send_json({"type": "auth_success"})
        admins.append(websocket)

        for cid in clients:
            await websocket.send_json({"type": "client_connected", "client_id": cid})

        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "command":
                target = msg.get("target")
                if target in clients:
                    await clients[target].send_text(json.dumps(msg.get("command")))
    except WebSocketDisconnect:
        if websocket in admins:
            admins.remove(websocket)
