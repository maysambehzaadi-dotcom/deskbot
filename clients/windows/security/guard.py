import ctypes
import os

class SecurityGuard:
    """
    سیستم تأییدیه بومی ویندوز برای عملیات حساس
    بدون نیاز به کتابخانه سنگین گرافیکی
    """
    MB_YESNO = 0x00000004
    MB_ICONWARNING = 0x00000030
    MB_TOPMOST = 0x00040000
    IDYES = 6

    # دستوراتی که پیش‌فرض حساس در نظر گرفته می‌شوند
    SENSITIVE_KEYWORDS = [
        "rmdir", "remove-item", "del", "format", "shutdown", 
        "restart-computer", "stop-process", "reg delete", "net user"
    ]

    @classmethod
    def is_command_sensitive(cls, command: str) -> bool:
        cmd_lower = command.lower()
        return any(kw in cmd_lower for kw in cls.SENSITIVE_KEYWORDS)

    @classmethod
    def prompt_user_approval(cls, action_type: str, details: str) -> bool:
        title = "میزکار دیجیتال (DeskBot) - تأیید مجوز"
        message = (
            f"ایجنت می‌خواهد عملیات زیر را انجام دهد:\n\n"
            f"نوع عملیات: {action_type}\n"
            f"جزئیات:\n{details[:400]}\n\n"
            f"آیا اجازه اجرای این عملیات را می‌دهید؟"
        )
        try:
            res = ctypes.windll.user32.MessageBoxW(
                0,
                message,
                title,
                cls.MB_YESNO | cls.MB_ICONWARNING | cls.MB_TOPMOST
            )
            return res == cls.IDYES
        except Exception:
            # در صورتی که دیالوگ به هر دلیلی باز نشد، جهت حفظ امنیت ریجکت می‌شود
            return False
