import subprocess
import os

class ShellRunner:
    """
    اجرای کاملاً نامرئی و پس‌زمینه دستورات PowerShell و CMD
    بدون باز شدن پنجره سیاه یا درگیر کردن فوکوس سیستم
    """
    CREATE_NO_WINDOW = 0x08000000

    @staticmethod
    def run_powershell(command: str, timeout: int = 120) -> dict:
        try:
            # Bypass execution policy and run without profile for maximum speed
            full_cmd = [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-Command", command
            ]

            process = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=ShellRunner.CREATE_NO_WINDOW,
                timeout=timeout
            )

            return {
                "exit_code": process.returncode,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "success": process.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds.",
                "success": False
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            }

    @staticmethod
    def run_cmd(command: str, timeout: int = 120) -> dict:
        try:
            process = subprocess.run(
                ["cmd.exe", "/c", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=ShellRunner.CREATE_NO_WINDOW,
                timeout=timeout
            )
            return {
                "exit_code": process.returncode,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "success": process.returncode == 0
            }
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e), "success": False}
