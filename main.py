from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

clients = {}

@app.get("/")
async def root():
    return HTMLResponse("""
    <html>
      <body>
        <h1>WebSocket Manager</h1>
        <input id="cmd" placeholder="Command" />
        <button onclick="sendCmd()">Send</button>
        <pre id="log"></pre>
        <script>
          let ws = new WebSocket("wss://" + location.host + "/ws/admin");
          ws.onmessage = event => {
            document.getElementById("log").textContent += event.data + "\n";
          };
          function sendCmd() {
            let cmd = document.getElementById("cmd").value;
            ws.send(cmd);
          }
        </script>
      </body>
    </html>
    """)

@app.websocket("/ws/{client_id}")
async def client_ws(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    try:
        while True:
            msg = await websocket.receive_text()
            if "admin" in clients:
                await clients["admin"].send(f"[{client_id}] {msg}")
    except WebSocketDisconnect:
        clients.pop(client_id)

@app.websocket("/ws/admin")
async def admin_ws(websocket: WebSocket):
    await websocket.accept()
    clients["admin"] = websocket
    try:
        while True:
            cmd = await websocket.receive_text()
            for cid, ws in clients.items():
                if cid != "admin":
                    await ws.send(cmd)
    except WebSocketDisconnect:
        clients.pop("admin")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
