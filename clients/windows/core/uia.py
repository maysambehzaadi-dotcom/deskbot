import subprocess
import json

class UIAutomationRunner:
    """
    اتوماسیون نرم‌افزارهای پنجره‌ای ویندوز با Windows UI Automation (UIA)
    کلیک روی دکمه‌ها و خواندن المنت‌ها بدون تکان دادن ماوس فیزیکی
    """
    CREATE_NO_WINDOW = 0x08000000

    @staticmethod
    def list_open_windows() -> dict:
        """لیست کردن تمام پنجره‌های فعال دسکتاپ"""
        ps_script = """
        Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            using System.Text;
            public class WindowEnumerator {
                [DllImport("user32.dll")]
                public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
                [DllImport("user32.dll")]
                public static extern bool IsWindowVisible(IntPtr hWnd);
                [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
                public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
                public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            }
"@
        $windows = @()
        [WindowEnumerator]::EnumWindows({
            param($hwnd, $lparam)
            if ([WindowEnumerator]::IsWindowVisible($hwnd)) {
                $sb = New-Object System.Text.StringBuilder 256
                $len = [WindowEnumerator]::GetWindowText($hwnd, $sb, $sb.Capacity)
                if ($len -gt 0) {
                    $title = $sb.ToString()
                    if ($title -ne "Program Manager") {
                        $script:windows += [PSCustomObject]@{ Handle = $hwnd.ToInt64(); Title = $title }
                    }
                }
            }
            return $true
        }, 0) | Out-Null
        $windows | ConvertTo-Json -Compress
        """
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=UIAutomationRunner.CREATE_NO_WINDOW,
                timeout=15
            )
            stdout = res.stdout.strip()
            if not stdout:
                return {"success": True, "windows": []}
            return {"success": True, "windows": json.loads(stdout)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def invoke_button(window_title: str, control_name: str) -> dict:
        """
        ارسال دستور کلیک مستقیم روی دکمه بدون جابجایی ماوس از طریق UI Automation
        """
        ps_script = f"""
        Add-Type -AssemblyName UIAutomationClient
        Add-Type -AssemblyName UIAutomationTypes

        $root = [System.Windows.Automation.AutomationElement]::RootElement
        $condWindow = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, "{window_title}"
        )
        $win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $condWindow)
        if (-not $win) {{
            Write-Output "ERROR: Window not found"
            exit
        }}

        $condBtn = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, "{control_name}"
        )
        $btn = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condBtn)
        if (-not $btn) {{
            Write-Output "ERROR: Control not found"
            exit
        }}

        $invokePattern = $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        if ($invokePattern) {{
            $invokePattern.Invoke()
            Write-Output "SUCCESS"
        }} else {{
            Write-Output "ERROR: Element does not support InvokePattern"
        }}
        """
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=UIAutomationRunner.CREATE_NO_WINDOW,
                timeout=20
            )
            out = res.stdout.strip()
            if "SUCCESS" in out:
                return {"success": True, "message": f"Clicked control '{control_name}' in '{window_title}'"}
            return {"success": False, "error": out}
        except Exception as e:
            return {"success": False, "error": str(e)}
