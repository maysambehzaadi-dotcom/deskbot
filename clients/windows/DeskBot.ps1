<#
.SYNOPSIS
    DeskBot Windows Native Client (بدون نیاز به نصب پایتون یا هر ابزار جانبی)
    مستقیماً با پاورشل بومی ویندوز اجرا می‌شود و با سرور رله ارتباط می‌گیرد.
#>

param(
    [string]$RelayUrl = "ws://185.194.191.178:4001/ws/device",
    [string]$DeviceId = "win-$($env:COMPUTERNAME.ToLower())",
    [switch]$AutoApprove
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       DeskBot - عامل اجرایی میز کار ویندوز              " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[*] شناسه دستگاه: $DeviceId" -ForegroundColor Yellow
Write-Host "[*] اتصال به سرور: $RelayUrl/$DeviceId" -ForegroundColor Yellow

function Prompt-Approval([string]$action, [string]$details) {
    if ($AutoApprove) { return $true }
    $msg = "ایجنت می‌خواهد عملیات زیر را انجام دهد:`n`nنوع: $action`nجزئیات:`n$details`n`nآیا اجازه می‌دهید؟"
    $res = [System.Windows.Forms.MessageBox]::Show($msg, "DeskBot Security", [System.Windows.Forms.MessageBoxButtons]::YesNo, [System.Windows.Forms.MessageBoxIcon]::Question)
    return ($res -eq [System.Windows.Forms.DialogResult]::Yes)
}

function Execute-Tool([string]$tool, [hashtable]$args) {
    switch ($tool) {
        "shell.powershell" {
            $cmd = $args["command"]
            if ($cmd -match "rmdir|remove-item|del|format|shutdown|stop-process") {
                if (-not (Prompt-Approval "PowerShell Command" $cmd)) {
                    return @{ success = $false; error = "توسط کاربر لغو شد." }
                }
            }
            try {
                $out = Invoke-Expression $cmd | Out-String
                return @{ success = $true; stdout = $out.Trim(); exit_code = 0 }
            } catch {
                return @{ success = $false; stderr = $_.Exception.Message; exit_code = 1 }
            }
        }
        "fs.read" {
            $path = $args["path"]
            if (Test-Path $path) {
                return @{ success = $true; content = (Get-Content $path -Raw -Encoding UTF8) }
            }
            return @{ success = $false; error = "فایل یافت نشد: $path" }
        }
        "fs.write" {
            $path = $args["path"]
            $content = $args["content"]
            $dir = Split-Path $path -Parent
            if ($dir -and (-not (Test-Path $dir))) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            Set-Content -Path $path -Value $content -Encoding UTF8
            return @{ success = $true; path = $path }
        }
        "fs.list" {
            $path = if ($args["path"]) { $args["path"] } else { "." }
            if (Test-Path $path) {
                $items = Get-ChildItem -Path $path | Select-Object Name, Length, @{Name="IsDir"; Expression={$_.PSIsContainer}}
                return @{ success = $true; items = $items }
            }
            return @{ success = $false; error = "مسیر یافت نشد: $path" }
        }
        default {
            return @{ success = $false; error = "ابزار ناشناخته: $tool" }
        }
    }
}

# حلقه اصلی اتصال WebSocket با استفاده از .NET بومی
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$uri = New-Object System.Uri("$RelayUrl/$DeviceId")
$cts = New-Object System.Threading.CancellationTokenSource

try {
    $ws.ConnectAsync($uri, $cts.Token).Wait()
    Write-Host "[✓] متصل شد به سرور مرکزی DeskBot!" -ForegroundColor Green

    # ارسال پیام ثبت اولیه
    $init = @{ os = "windows"; hostname = $env:COMPUTERNAME } | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($init)
    $segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$bytes)
    $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).Wait()

    $buffer = New-Object byte[] 65536
    while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        $recvSegment = New-Object System.ArraySegment[byte] -ArgumentList @(,$buffer)
        $recvResult = $ws.ReceiveAsync($recvSegment, $cts.Token).Result
        if ($recvResult.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
            break
        }
        
        $jsonStr = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $recvResult.Count)
        $msg = $jsonStr | ConvertFrom-Json
        
        if ($msg.call_id) {
            Write-Host "[*] دریافت دستور: $($msg.tool)" -ForegroundColor Cyan
            $argsTable = @{}
            if ($msg.args) {
                $msg.args.psobject.properties | ForEach-Object { $argsTable[$_.Name] = $_.Value }
            }
            $result = Execute-Tool $msg.tool $argsTable
            
            $resp = @{ call_id = $msg.call_id; result = $result } | ConvertTo-Json -Compress -Depth 5
            $respBytes = [System.Text.Encoding]::UTF8.GetBytes($resp)
            $respSeg = New-Object System.ArraySegment[byte] -ArgumentList @(,$respBytes)
            $ws.SendAsync($respSeg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).Wait()
            Write-Host "[✓] پاسخ دستور ارسال شد." -ForegroundColor Green
        }
    }
} catch {
    Write-Host "[X] خطا در اتصال: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if ($ws) { $ws.Dispose() }
}
