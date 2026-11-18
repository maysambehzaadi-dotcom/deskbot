<#
.SYNOPSIS
    کارشناس هوشمند خرید و سلامت سیستم - DeskBot Client
    بدون نیاز به پایتون یا هر پیش‌نیاز دیگر.
    مشخصات را جمع‌آوری کرده، به مغز هوش مصنوعی در سرور ارسال می‌کند و گزارش زنده گرافیکی تحویل می‌دهد.
#>

param(
    [string]$ServerUrl = "http://185.194.191.178:4001/api/v1/inspect-system"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       کارشناس هوشمند اصالت و سلامت سیستم (DeskBot)      " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] در حال بررسی قطعات سخت‌افزاری، سلامت باتری و پایداری ویندوز..." -ForegroundColor Yellow

try {
    # 1. استخراج مشخصات سیستم
    $CS = Get-CimInstance Win32_ComputerSystem
    $BIOS = Get-CimInstance Win32_Bios
    $CPU = Get-CimInstance Win32_Processor | Select-Object -First 1
    $RAMModules = Get-CimInstance Win32_PhysicalMemory
    $TotalRAM = [math]::Round(($RAMModules | Measure-Object -Property Capacity -Sum).Sum / 1GB, 1)
    $GPUs = (Get-CimInstance Win32_VideoController).Name -join " + "
    $OS = Get-CimInstance Win32_OperatingSystem

    # 2. بررسی باتری (لپ‌تاپ)
    $BatStatic = Get-CimInstance -Namespace root\wmi -ClassName BatteryStaticData -ErrorAction SilentlyContinue
    $BatFull = Get-CimInstance -Namespace root\wmi -ClassName BatteryFullChargedCapacity -ErrorAction SilentlyContinue
    $BatCycle = Get-CimInstance -Namespace root\wmi -ClassName BatteryCycleCount -ErrorAction SilentlyContinue
    
    $BatHealthPercent = -1.0
    $BatCycles = "دسکتاپ (فاقد باتری)"
    if ($BatStatic -and $BatFull -and $BatStatic.DesignedCapacity -gt 0) {
        $BatHealthPercent = [math]::Round(($BatFull.FullChargedCapacity / $BatStatic.DesignedCapacity) * 100, 1)
        $BatCycles = if ($BatCycle.CycleCount) { $BatCycle.CycleCount } else { "نامشخص" }
    }

    # 3. بررسی دیسک‌ها
    $DisksList = @()
    foreach ($d in (Get-PhysicalDisk)) {
        $Rel = Get-StorageReliabilityCounter -PhysicalDisk $d -ErrorAction SilentlyContinue
        $Hours = if ($Rel -and $Rel.PowerOnHours) { [int]$Rel.PowerOnHours } else { 0 }
        $Wear = if ($Rel -and $Rel.Wear) { [int]$Rel.Wear } else { 0 }
        $DisksList += @{
            name = $d.FriendlyName
            size_gb = [math]::Round($d.Size/1GB)
            media_type = "$($d.MediaType)"
            power_on_hours = $Hours
            wear_percent = $Wear
        }
    }

    # 4. بررسی کرش‌ها
    $Crashes = (Get-WinEvent -FilterHashtable @{LogName='System'; Id=41} -MaxEvents 5 -ErrorAction SilentlyContinue | Measure-Object).Count
    $UptimeHours = [math]::Round(((Get-Date) - $OS.LastBootUpTime).TotalHours, 1)

    # 5. آماده‌سازی بدنه JSON
    $Payload = @{
        manufacturer = if ($CS.Manufacturer) { "$($CS.Manufacturer)" } else { "نامشخص" }
        model = if ($CS.Model) { "$($CS.Model)" } else { "نامشخص" }
        serial_number = if ($BIOS.SerialNumber) { "$($BIOS.SerialNumber)" } else { "نامشخص" }
        cpu_name = if ($CPU.Name) { "$($CPU.Name)" } else { "نامشخص" }
        cpu_cores = if ($CPU.NumberOfCores) { [int]$CPU.NumberOfCores } else { 1 }
        cpu_threads = if ($CPU.NumberOfLogicalProcessors) { [int]$CPU.NumberOfLogicalProcessors } else { 1 }
        ram_gb = [float]$TotalRAM
        ram_slots = if ($RAMModules.Count) { [int]$RAMModules.Count } else { 1 }
        gpus = if ($GPUs) { "$GPUs" } else { "نامشخص" }
        battery_health_percent = [float]$BatHealthPercent
        battery_cycles = "$BatCycles"
        disks = $DisksList
        crashes_count = [int]$Crashes
        windows_version = "$($OS.Caption)"
        uptime_hours = [float]$UptimeHours
    } | ConvertTo-Json -Depth 5

    Write-Host "[*] ارسال داده‌ها به مغز کارشناسی هوش مصنوعی در سرور..." -ForegroundColor Cyan

    $Response = Invoke-RestMethod -Uri $ServerUrl -Method Post -Body $Payload -ContentType "application/json; charset=utf-8"

    if ($Response.success) {
        Write-Host "`n[✓] نتیجه کارشناسی دریافت شد!" -ForegroundColor Green
        Write-Host "    امتیاز سیستم: $($Response.score) از ۱۰۰" -ForegroundColor Yellow
        Write-Host "    نظر کارشناس: $($Response.verdict)" -ForegroundColor White

        # ذخیره و باز کردن گزارش شیک HTML
        $ReportPath = Join-Path $env:TEMP "SystemExpert_Report.html"
        [System.IO.File]::WriteAllText($ReportPath, $Response.html_report, [System.Text.Encoding]::UTF8)

        Start-Process $ReportPath
    } else {
        Write-Host "[X] سرور نتیجه را تایید نکرد." -ForegroundColor Red
    }

} catch {
    Write-Host "[X] خطا در تحلیل: $($_.Exception.Message)" -ForegroundColor Red
}
