import asyncio
import websockets
import json

# Verbundene Clients und Admins
clients = {}   # client_id -> websocket
admins = set() # set of admin websockets

# Konstantes Passwort
ADMIN_PASSWORD = "supersecurepassword"

async def handler(websocket, path):
    client_id = None

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            # === Admin-Verbindung ===
            if path == "/ws/admin/":
                if msg_type == "auth":
                    if data.get("password") == ADMIN_PASSWORD:
                        admins.add(websocket)
                        await websocket.send(json.dumps({"type": "auth_success"}))
                        print("✅ Admin verbunden")
                        # Informiere Admin über bestehende Clients
                        for cid in clients:
                            await websocket.send(json.dumps({"type": "client_connected", "client_id": cid}))
                    else:
                        await websocket.send(json.dumps({"type": "auth_failed"}))
                        await websocket.close()
                        return

                elif msg_type == "command":
                    target = data.get("target")
                    command = data.get("command")
                    if target in clients:
                        await clients[target].send(json.dumps(command))

            # === Client-Verbindung ===
            elif path.startswith("/ws/client/"):
                client_id = path.split("/")[-1]
                clients[client_id] = websocket
                print(f"🟢 Client verbunden: {client_id}")

                # Admins benachrichtigen
                for admin in admins:
                    try:
                        await admin.send(json.dumps({"type": "client_connected", "client_id": client_id}))
                    except:
                        continue

            # === Nachricht vom Client (Weiterleiten) ===
            if msg_type in ("screen_frame", "cmd_result", "process_list"):
                for admin in admins:
                    try:
                        await admin.send(json.dumps(data))
                    except:
                        continue

    except websockets.exceptions.ConnectionClosed:
        print("❌ Verbindung geschlossen")

    finally:
        if path.startswith("/ws/client/") and client_id:
            if clients.get(client_id) == websocket:
                del clients[client_id]
            for admin in admins:
                try:
                    await admin.send(json.dumps({"type": "client_disconnected", "client_id": client_id}))
                except:
                    continue

        elif path == "/ws/admin/":
            admins.discard(websocket)

        try:
            if not websocket.closed:
                await websocket.close()
        except:
            pass

async def main():
    print("🌐 Starte Server auf ws://0.0.0.0:10000")
    async with websockets.serve(handler, "0.0.0.0", 10000):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
