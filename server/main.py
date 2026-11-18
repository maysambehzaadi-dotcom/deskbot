import asyncio
import json
import logging
import uuid
import os
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DeskBotRelay")

app = FastAPI(
    title="DeskBot Central Relay & AI Inspector",
    description="Central server connecting AI orchestrators with endpoint device actuators.",
    version="1.1.0"
)

# ----------------- Device Management & Tool Relay -----------------
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
        "service": "DeskBot Central Relay & AI Inspector",
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

    payload = {"call_id": call_id, "tool": req.tool, "args": req.args}
    
    try:
        await device.ws.send_json(payload)
        result = await asyncio.wait_for(future, timeout=float(req.timeout))
        return {"call_id": call_id, "device_id": req.device_id, "tool": req.tool, "success": True, "result": result}
    except asyncio.TimeoutError:
        device.pending_calls.pop(call_id, None)
        raise HTTPException(status_code=504, detail="Command execution timed out on target device.")
    except Exception as e:
        device.pending_calls.pop(call_id, None)
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- AI System Expert Evaluation Engine -----------------
class SystemTelemetry(BaseModel):
    manufacturer: str = "نامشخص"
    model: str = "نامشخص"
    serial_number: str = "نامشخص"
    cpu_name: str = "نامشخص"
    cpu_cores: int = 1
    cpu_threads: int = 1
    ram_gb: float = 0.0
    ram_slots: int = 1
    gpus: str = "نامشخص"
    battery_health_percent: float = -1.0 # -1 means desktop / no battery
    battery_cycles: Any = "نامشخص"
    disks: List[Dict[str, Any]] = []
    crashes_count: int = 0
    windows_version: str = "نامشخص"
    uptime_hours: float = 0.0

def evaluate_system_intelligence(data: SystemTelemetry) -> Dict[str, Any]:
    score = 100
    pros = []
    cons = []
    warnings = []

    # 1. باتری
    if data.battery_health_percent >= 0:
        if data.battery_health_percent >= 85:
            pros.append(f"سلامت باتری فوق‌العاده ({data.battery_health_percent}٪)")
        elif data.battery_health_percent >= 70:
            score -= 10
            pros.append(f"سلامت باتری قابل قبول ({data.battery_health_percent}٪)")
        else:
            score -= 25
            cons.append(f"باتری دچار افت شدید است ({data.battery_health_percent}٪) - احتمال نیاز به تعویض")
            warnings.append("هزینه تعویض باتری در خرید لحاظ شود.")
    else:
        pros.append("سیستم دسکتاپ یا اتصال مستقیم به برق (فاقد استهلاک باتری)")

    # 2. رم
    if data.ram_gb >= 16:
        pros.append(f"میزان رم ایده‌آل برای کارهای سنگین و مدرن ({data.ram_gb} GB)")
    elif data.ram_gb >= 8:
        pros.append(f"میزان رم مناسب امور روزمره و اداری ({data.ram_gb} GB)")
    else:
        score -= 20
        cons.append(f"رم پایین ({data.ram_gb} GB) - احتمال کندی در مالتی‌تسکینگ")

    # 3. پایداری و کرش
    if data.crashes_count == 0:
        pros.append("پایداری سخت‌افزاری عالی (هیچ خاموشی ناگهانی اخیر ثبت نشده)")
    elif data.crashes_count <= 2:
        score -= 10
        cons.append(f"{data.crashes_count} مورد خاموشی ناگهانی یا کرش کرنل ثبت شده است")
    else:
        score -= 30
        cons.append(f"هشدار جدی: {data.crashes_count} بار خاموشی ناگهانی یا BlueScreen ثبت شده!")
        warnings.append("احتمال ایراد در پاور، رم یا مادربرد وجود دارد.")

    # 4. دیسک‌ها
    has_ssd = False
    for d in data.disks:
        media = str(d.get("media_type", "")).lower()
        if "ssd" in media or "nvme" in media:
            has_ssd = True
        hours = d.get("power_on_hours")
        if hours and hours > 20000:
            score -= 10
            cons.append(f"کارکرد بسیار بالای هارد ({hours} ساعت کار مداوم)")

    if has_ssd:
        pros.append("مجهز به حافظه پرسرعت SSD")
    else:
        score -= 15
        cons.append("فاقد حافظه SSD پرسرعت (کاهش سرعت بوت و اجرای برنامه‌ها)")

    score = max(20, min(100, score))

    # نتیجه‌گیری کارشناسی
    if score >= 85:
        verdict = "دستگاه کاملاً سالم، پایدار و با ارزش خرید بالا ارزیابی می‌شود."
        verdict_badge = "پیشنهاد عالی برای خرید"
        badge_color = "#10b981"
    elif score >= 70:
        verdict = "دستگاه از نظر فنی سالم است، با در نظر گرفتن نکات اعلام‌شده ارزش خرید دارد."
        verdict_badge = "ارزش خرید متوسط تا خوب"
        badge_color = "#3b82f6"
    else:
        verdict = "دستگاه دارای نقاط ضعف جدی است و خرید آن نیازمند بررسی دقیق فنی حضوری و تخفیف قیمت است."
        verdict_badge = "ریسک خرید بالا"
        badge_color = "#ef4444"

    return {
        "score": score,
        "verdict": verdict,
        "verdict_badge": verdict_badge,
        "badge_color": badge_color,
        "pros": pros,
        "cons": cons,
        "warnings": warnings
    }

def generate_html_report(data: SystemTelemetry, eval_res: Dict[str, Any]) -> str:
    pros_html = "".join([f"<li style='color: #065f46;'>✓ {p}</li>" for p in eval_res["pros"]])
    cons_html = "".join([f"<li style='color: #991b1b;'>✗ {c}</li>" for c in eval_res["cons"]])
    warn_html = "".join([f"<div style='background: #fef2f2; border-right: 4px solid #ef4444; padding: 10px; margin-bottom: 8px; border-radius: 4px; color: #991b1b;'>⚠️ {w}</div>" for w in eval_res["warnings"]])

    bat_text = f"{data.battery_health_percent}٪ (سایکل: {data.battery_cycles})" if data.battery_health_percent >= 0 else "دسکتاپ (فاقد باتری)"

    html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>گزارش کارشناسی هوشمند سیستم - DeskBot</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f8fafc; margin: 0; padding: 25px; color: #1e293b; }}
        .card {{ max-width: 780px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.08); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 25px 30px; display: flex; justify-content: space-between; align-items: center; }}
        .score-circle {{ width: 80px; height: 80px; border-radius: 50%; background: {eval_res['badge_color']}; color: white; display: flex; flex-direction: column; justify-content: center; align-items: center; font-weight: bold; font-size: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .score-circle span {{ font-size: 11px; font-weight: normal; }}
        .content {{ padding: 30px; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 14px; background: {eval_res['badge_color']}; color: white; margin-bottom: 12px; }}
        .verdict-box {{ background: #f1f5f9; padding: 16px 20px; border-radius: 12px; margin-bottom: 25px; font-size: 15px; line-height: 1.6; border-right: 5px solid {eval_res['badge_color']}; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px; }}
        .metric-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; }}
        .metric-card h4 {{ margin: 0 0 6px 0; font-size: 13px; color: #64748b; }}
        .metric-card p {{ margin: 0; font-weight: bold; font-size: 15px; color: #0f172a; }}
        .list-box {{ margin-bottom: 20px; }}
        ul {{ padding-right: 20px; margin: 8px 0; }}
        li {{ margin-bottom: 6px; font-size: 14px; line-height: 1.5; }}
        .footer {{ text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding: 15px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div>
                <h2 style="margin: 0 0 6px 0;">کارشناسی هوشمند اصالت و سلامت سیستم</h2>
                <div style="font-size: 13px; opacity: 0.85;">دستگاه: {data.manufacturer} {data.model} | سریال: {data.serial_number}</div>
            </div>
            <div class="score-circle">
                {eval_res['score']}
                <span>از ۱۰۰</span>
            </div>
        </div>
        <div class="content">
            <span class="badge">{eval_res['verdict_badge']}</span>
            <div class="verdict-box">
                <strong>نتیجه کارشناسی هوش مصنوعی:</strong><br>
                {eval_res['verdict']}
            </div>

            {warn_html}

            <div class="grid">
                <div class="metric-card">
                    <h4>پردازنده (CPU)</h4>
                    <p>{data.cpu_name}</p>
                </div>
                <div class="metric-card">
                    <h4>حافظه رم (RAM)</h4>
                    <p>{data.ram_gb} GB ({data.ram_slots} ماژول)</p>
                </div>
                <div class="metric-card">
                    <h4>وضعیت باتری لپ‌تاپ</h4>
                    <p>{bat_text}</p>
                </div>
                <div class="metric-card">
                    <h4>پایداری و سابقه کرش</h4>
                    <p>{'فاقد کرش اخیر (عالی)' if data.crashes_count == 0 else f'{data.crashes_count} بار کرش ثبت شده'}</p>
                </div>
            </div>

            <div class="list-box">
                <h4 style="margin: 0; color: #065f46;">نقاط قوت سیستم:</h4>
                <ul>{pros_html}</ul>
            </div>

            {f'<div class="list-box"><h4 style="margin: 0; color: #991b1b;">نکات احتیاط و ضعف:</h4><ul>{cons_html}</ul></div>' if eval_res['cons'] else ''}

        </div>
        <div class="footer">
            بررسی‌شده توسط پلتفرم DeskBot هوش مصنوعی ریوکسو (Rewaxoo)
        </div>
    </div>
</body>
</html>
"""
    return html

@app.post("/api/v1/inspect-system")
async def inspect_system_endpoint(data: SystemTelemetry):
    eval_result = evaluate_system_intelligence(data)
    html_report = generate_html_report(data, eval_result)
    return {
        "success": True,
        "score": eval_result["score"],
        "verdict": eval_result["verdict"],
        "verdict_badge": eval_result["verdict_badge"],
        "html_report": html_report
    }
