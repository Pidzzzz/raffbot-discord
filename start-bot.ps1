param(
    [switch]$Install,
    [switch]$Remove,
    [switch]$NoWatch
)

$BotDir = $PSScriptRoot
$ScriptName = "Raffbot-priv"

function Stop-ExistingBot {
    $processes = Get-CimInstance Win32_Process -Filter "name = 'python.exe'" -ErrorAction SilentlyContinue
    if ($processes) {
        foreach ($p in $processes) {
            if ($p.CommandLine -like "*bot.py*") {
                Write-Host "[$ScriptName] Stopping existing bot process (PID: $($p.ProcessId)) -> $($p.CommandLine)" -ForegroundColor Yellow
                Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 2
    }
}

function Install-Startup {
    $startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
    if (-not (Test-Path $startupDir)) {
        New-Item -ItemType Directory -Path $startupDir -Force | Out-Null
    }
    $shortcut = "$startupDir\Raffbot-priv.lnk"
    $wshell = New-Object -ComObject WScript.Shell
    $link = $wshell.CreateShortcut($shortcut)
    $link.TargetPath = "powershell.exe"
    $link.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$BotDir\start-bot.ps1`""
    $link.Description = "Raffbot-priv Auto-Start"
    $link.WorkingDirectory = $BotDir
    $link.Save()
    Write-Host "[$ScriptName] Startup shortcut successfully installed! The bot will now start automatically when Windows boots." -ForegroundColor Cyan
}

function Remove-Startup {
    $shortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Raffbot-priv.lnk"
    if (Test-Path $shortcut) { 
        Remove-Item $shortcut
        Write-Host "[$ScriptName] Startup shortcut removed." -ForegroundColor Yellow
    }
    Stop-ExistingBot
}

function Start-Watcher {
    Write-Host "[$ScriptName] Checking dependencies..." -ForegroundColor Cyan
    pip install -r "$BotDir\requirements.txt" | Out-Null

    Stop-ExistingBot

    Write-Host "[$ScriptName] Hot-reload mode active. Monitoring code changes..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C in this console to exit." -ForegroundColor Gray

    while ($true) {
        Write-Host "[$ScriptName] Starting Discord Bot..." -ForegroundColor Green
        
        $process = Start-Process python -ArgumentList "$BotDir\bot.py" -WorkingDirectory $BotDir -NoNewWindow -PassThru
        
        $files = Get-ChildItem -Path $BotDir -Recurse -Include *.py, *.env, *.json | Where-Object { 
            $_.FullName -notlike "*temp*" -and $_.FullName -notlike "*journal.json*" -and $_.FullName -notlike "*reminders.json*" 
        }
        
        $fileStates = @{}
        foreach ($file in $files) {
            $fileStates[$file.FullName] = $file.LastWriteTime
        }
        
        $changed = $false
        while (-not $changed -and -not $process.HasExited) {
            Start-Sleep -Seconds 2
            
            $currentFiles = Get-ChildItem -Path $BotDir -Recurse -Include *.py, *.env, *.json | Where-Object { 
                $_.FullName -notlike "*temp*" -and $_.FullName -notlike "*journal.json*" -and $_.FullName -notlike "*reminders.json*" 
            }
            
            if ($currentFiles.Count -ne $files.Count) {
                $changed = $true
                break
            }
            
            foreach ($file in $currentFiles) {
                if (-not $fileStates.ContainsKey($file.FullName) -or $fileStates[$file.FullName] -ne $file.LastWriteTime) {
                    Write-Host "[$ScriptName] File changed: $($file.Name)" -ForegroundColor Magenta
                    $changed = $true
                    break
                }
            }
        }
        
        if ($process.HasExited) {
            Write-Host "[$ScriptName] Process exited. Restarting in 3 seconds..." -ForegroundColor Red
            Start-Sleep -Seconds 3
        } elseif ($changed) {
            Write-Host "[$ScriptName] Code changes detected! Restarting bot..." -ForegroundColor Yellow
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    }
}

function Start-Simple {
    Write-Host "[$ScriptName] Checking dependencies..." -ForegroundColor Cyan
    pip install -r "$BotDir\requirements.txt" | Out-Null

    Stop-ExistingBot
    
    Write-Host "[$ScriptName] Starting Discord Bot..." -ForegroundColor Green
    Start-Process python -ArgumentList "$BotDir\bot.py" -WorkingDirectory $BotDir -NoNewWindow
}

if ($Install) {
    Install-Startup
    Start-Simple
} elseif ($Remove) {
    Remove-Startup
} else {
    if ($NoWatch) {
        Start-Simple
    } else {
        Start-Watcher
    }
}
