import asyncio
import json
import logging
import uuid
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DeskBotRelay")

app = FastAPI(
    title="DeskBot Central Relay",
    description="Central server connecting AI orchestrators with endpoint device actuators.",
    version="1.0.0"
)

class ActiveDevice:
    def __init__(self, ws: WebSocket, os_type: str, hostname: str):
        self.ws = ws
        self.os_type = os_type
        self.hostname = hostname
        self.pending_calls: Dict[str, asyncio.Future] = {}

connected_devices: Dict[str, ActiveDevice] = {}

class CommandRequest(BaseModel):
    device_id: str
    tool: str
    args: Dict[str, Any] = {}
    timeout: int = 60

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "DeskBot Central Relay",
        "active_devices_count": len(connected_devices),
        "devices": [
            {"id": did, "os": dev.os_type, "hostname": dev.hostname}
            for did, dev in connected_devices.items()
        ]
    }

@app.websocket("/ws/device/{device_id}")
async def device_websocket_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    logger.info(f"Incoming device connection: {device_id}")
    try:
        # Wait for handshake
        init_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        os_type = init_data.get("os", "windows")
        hostname = init_data.get("hostname", "unknown")
        
        device = ActiveDevice(websocket, os_type, hostname)
        connected_devices[device_id] = device
        logger.info(f"Device authenticated: {device_id} ({os_type} on {hostname})")
        
        await websocket.send_json({"type": "auth_ack", "status": "authenticated", "device_id": device_id})

        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            call_id = data.get("call_id")
            if call_id and call_id in device.pending_calls:
                future = device.pending_calls.pop(call_id)
                if not future.done():
                    future.set_result(data.get("result"))
    except WebSocketDisconnect:
        logger.warning(f"Device disconnected: {device_id}")
    except Exception as e:
        logger.error(f"Error on device {device_id}: {e}")
    finally:
        connected_devices.pop(device_id, None)

@app.post("/api/v1/execute")
async def execute_tool_on_device(req: CommandRequest):
    device = connected_devices.get(req.device_id)
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{req.device_id}' is not connected. Connected devices: {list(connected_devices.keys())}"
        )

    call_id = f"call_{uuid.uuid4().hex[:10]}"
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    device.pending_calls[call_id] = future

    payload = {
        "call_id": call_id,
        "tool": req.tool,
        "args": req.args
    }
    
    try:
        await device.ws.send_json(payload)
        result = await asyncio.wait_for(future, timeout=float(req.timeout))
        return {
            "call_id": call_id,
            "device_id": req.device_id,
            "tool": req.tool,
            "success": True,
            "result": result
        }
    except asyncio.TimeoutError:
        device.pending_calls.pop(call_id, None)
        raise HTTPException(status_code=504, detail="Command execution timed out on target device.")
    except Exception as e:
        device.pending_calls.pop(call_id, None)
        raise HTTPException(status_code=500, detail=str(e))
