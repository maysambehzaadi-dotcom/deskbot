import subprocess
import json

class AndroidADBBridge:
    """
    کنترل گوشی اندروید از طریق ADB (محلی یا بی‌سیم)
    اجرای دستورات سیستم‌عامل، باز کردن اپ‌ها، شبیه‌سازی کلیدها و رویدادها
    """

    @staticmethod
    def get_connected_devices() -> list:
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            lines = res.stdout.strip().split("\n")[1:]
            devices = [line.split()[0] for line in lines if "device" in line]
            return devices
        except Exception as e:
            return []

    @staticmethod
    def run_shell(device_serial: str, command: str) -> dict:
        try:
            cmd = ["adb", "-s", device_serial, "shell", command] if device_serial else ["adb", "shell", command]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return {"success": res.returncode == 0, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def open_app(device_serial: str, package_name: str) -> dict:
        return AndroidADBBridge.run_shell(
            device_serial,
            f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        )
