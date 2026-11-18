import asyncio
import json
import logging
import platform
import socket
import os
import sys
import websockets

# اضافه کردن مسیر ماژول‌ها
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.shell import ShellRunner
from core.filesystem import FileSystemRunner
from core.uia import UIAutomationRunner
from security.guard import SecurityGuard

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DeskBotWindowsClient")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read config: {e}")
    # پیش‌فرض سرور اختصاصی VPS
    return {
        "relay_url": "ws://185.194.191.178:4001/ws/device",
        "device_id": f"win-{socket.gethostname().lower()}",
        "require_approval_for_sensitive": True
    }

async def dispatch_tool(tool_name: str, args: dict, config: dict) -> dict:
    logger.info(f"Executing tool: {tool_name} with args: {args}")
    
    # 1. ابزارهای شل
    if tool_name == "shell.powershell":
        cmd = args.get("command", "")
        if config.get("require_approval_for_sensitive") and SecurityGuard.is_command_sensitive(cmd):
            if not SecurityGuard.prompt_user_approval("PowerShell Command", cmd):
                return {"success": False, "error": "Operation rejected by user."}
        return ShellRunner.run_powershell(cmd, timeout=args.get("timeout", 120))

    elif tool_name == "shell.cmd":
        cmd = args.get("command", "")
        if config.get("require_approval_for_sensitive") and SecurityGuard.is_command_sensitive(cmd):
            if not SecurityGuard.prompt_user_approval("CMD Command", cmd):
                return {"success": False, "error": "Operation rejected by user."}
        return ShellRunner.run_cmd(cmd, timeout=args.get("timeout", 120))

    # 2. ابزارهای فایل
    elif tool_name == "fs.read":
        return FileSystemRunner.read_file(args.get("path", ""))

    elif tool_name == "fs.write":
        path = args.get("path", "")
        content = args.get("content", "")
        return FileSystemRunner.write_file(path, content, append=args.get("append", False))

    elif tool_name == "fs.list":
        return FileSystemRunner.list_dir(args.get("path", "."))

    elif tool_name == "fs.delete":
        path = args.get("path", "")
        if config.get("require_approval_for_sensitive"):
            if not SecurityGuard.prompt_user_approval("Delete File/Directory", path):
                return {"success": False, "error": "Deletion rejected by user."}
        return FileSystemRunner.delete(path)

    # 3. ابزارهای رابط کاربری بدون ماوس (UIA)
    elif tool_name == "uia.list_windows":
        return UIAutomationRunner.list_open_windows()

    elif tool_name == "uia.click":
        return UIAutomationRunner.invoke_button(
            args.get("window_title", ""),
            args.get("control_name", "")
        )

    else:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

async def run_client():
    config = load_config()
    server_ws_endpoint = f"{config['relay_url']}/{config['device_id']}"
    
    logger.info(f"DeskBot Windows Agent starting...")
    logger.info(f"Target Relay: {server_ws_endpoint}")

    while True:
        try:
            logger.info("Connecting to central relay...")
            async with websockets.connect(server_ws_endpoint) as ws:
                # Handshake
                handshake_payload = {
                    "os": "windows",
                    "hostname": socket.gethostname(),
                    "platform": platform.platform()
                }
                await ws.send(json.dumps(handshake_payload))

                auth_response = await ws.recv()
                logger.info(f"Server Handshake Response: {auth_response}")

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    call_id = data.get("call_id")
                    tool = data.get("tool")
                    args = data.get("args", {})

                    result = await dispatch_tool(tool, args, config)
                    
                    response_payload = {
                        "call_id": call_id,
                        "result": result
                    }
                    await ws.send(json.dumps(response_payload))

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            logger.warning(f"Connection lost ({e}). Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        logger.info("DeskBot Agent terminated by user.")
