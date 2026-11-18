import os
import shutil
import glob
from typing import List, Dict, Any

class FileSystemRunner:
    """
    عملیات مستقیم و باینری بر روی فایل‌ها و پوشه‌ها
    بدون نیاز به باز کردن هیچ اپلیکیشن ویرایشگر یا فایل‌منیجر
    """

    @staticmethod
    def read_file(path: str, max_bytes: int = 10 * 1024 * 1024) -> dict:
        try:
            full_path = os.path.abspath(os.path.expanduser(path))
            if not os.path.exists(full_path):
                return {"success": False, "error": f"File not found: {full_path}"}
            
            size = os.path.getsize(full_path)
            if size > max_bytes:
                return {"success": False, "error": f"File too large ({size} bytes, limit is {max_bytes})"}

            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"success": True, "path": full_path, "size": size, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def write_file(path: str, content: str, append: bool = False) -> dict:
        try:
            full_path = os.path.abspath(os.path.expanduser(path))
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            mode = "a" if append else "w"
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": full_path, "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_dir(path: str = ".") -> dict:
        try:
            full_path = os.path.abspath(os.path.expanduser(path))
            if not os.path.exists(full_path):
                return {"success": False, "error": f"Path not found: {full_path}"}

            items = []
            for entry in os.scandir(full_path):
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if entry.is_file() else 0,
                    "modified": entry.stat().st_mtime
                })
            return {"success": True, "path": full_path, "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete(path: str) -> dict:
        try:
            full_path = os.path.abspath(os.path.expanduser(path))
            if not os.path.exists(full_path):
                return {"success": False, "error": f"Path not found: {full_path}"}

            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
            return {"success": True, "deleted": full_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
