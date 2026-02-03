# Jill Launcher - Windows PowerShell
#
# This script starts Lavalink and the bot with proper health checking.
# Called by START-jill-win.bat (which handles ExecutionPolicy bypass)

#Requires -Version 5.1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ScriptDir

# Load .env file if present (for LAVALINK_PASSWORD override)
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#=][^=]*)=(.*)$') {
            $key = $Matches[1].Trim()
            $value = $Matches[2] -replace '\s+#.*$', ''  # Strip trailing comment
            $value = $value.Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Configuration
$LavalinkPort = if ($env:LAVALINK_PORT) { $env:LAVALINK_PORT } else { 4440 }
$LavalinkTimeout = 60
$LavalinkPassword = if ($env:LAVALINK_PASSWORD) { $env:LAVALINK_PASSWORD } else { "timetomixdrinksandnotchangepasswords" }
$LavalinkJar = "lavalink\Lavalink.jar"
$LavalinkConfig = "lavalink\application.yml"
$VenvPython = "venv\Scripts\python.exe"

# Track Lavalink process for cleanup
$script:LavalinkProcess = $null

function Test-LavalinkReady {
    try {
        $headers = @{ "Authorization" = $LavalinkPassword }
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$LavalinkPort/version" `
            -Headers $headers -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Get-JavaPath {
    # Try PATH first, then fall back to JAVA_PATH from batch file
    $javaCmd = Get-Command java -ErrorAction SilentlyContinue
    if ($javaCmd) {
        return $javaCmd.Source
    }
    if ($env:JAVA_PATH -and (Test-Path $env:JAVA_PATH)) {
        return $env:JAVA_PATH
    }
    return $null
}

function Get-JavaMajorVersion {
    $javaPath = Get-JavaPath
    if (-not $javaPath) {
        return 0
    }
    try {
        # java -version outputs to stderr; temporarily allow non-terminating errors
        # (ErrorActionPreference=Stop causes 2>&1 to throw instead of capture)
        $oldPref = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $output = & $javaPath -version 2>&1 | Out-String
        $ErrorActionPreference = $oldPref
        if ($output -match 'version "(\d+)') {
            return [int]$Matches[1]
        }
    } catch {}
    return 0
}

function Stop-LavalinkIfStarted {
    if ($script:LavalinkProcess -and -not $script:LavalinkProcess.HasExited) {
        Write-Host "stopping lavalink..."
        Stop-Process -Id $script:LavalinkProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

# Register cleanup handler
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-LavalinkIfStarted }
trap { Stop-LavalinkIfStarted; break }

# Validation
Write-Host "=== JILL STARTUP ===" -ForegroundColor Magenta
Write-Host

# Check venv
if (-not (Test-Path $VenvPython)) {
    Write-Host "[x] virtual environment not found." -ForegroundColor Red
    Write-Host "    run setup-jill-win.bat first."
    exit 1
}
Write-Host "[+] virtual environment found" -ForegroundColor Cyan

# Check Java version
$javaVersion = Get-JavaMajorVersion
if ($javaVersion -eq 0) {
    Write-Host "[x] java 17+ required for lavalink." -ForegroundColor Red
    Write-Host ""
    Write-Host "    1. download from: https://adoptium.net/temurin/releases/"
    Write-Host "       select: windows x64, JRE, version 17+, .msi installer"
    Write-Host "    2. run the installer"
    Write-Host "    3. restart this terminal and try again"
    exit 1
}
if ($javaVersion -lt 17) {
    Write-Host "[x] java 17+ required, found java $javaVersion" -ForegroundColor Red
    Write-Host ""
    Write-Host "    1. download from: https://adoptium.net/temurin/releases/"
    Write-Host "       select: windows x64, JRE, version 17+, .msi installer"
    Write-Host "    2. run the installer"
    Write-Host "    3. restart this terminal and try again"
    exit 1
}
Write-Host "[+] java $javaVersion" -ForegroundColor Cyan

# Check Lavalink files
if (-not (Test-Path $LavalinkJar)) {
    Write-Host "[x] $LavalinkJar not found." -ForegroundColor Red
    Write-Host "    download from: https://github.com/lavalink-devs/Lavalink/releases"
    exit 1
}
Write-Host "[+] lavalink.jar found" -ForegroundColor Cyan

if (-not (Test-Path $LavalinkConfig)) {
    Write-Host "[x] $LavalinkConfig not found." -ForegroundColor Red
    exit 1
}
Write-Host "[+] application.yml found" -ForegroundColor Cyan

# Start Lavalink if not running
if (Test-LavalinkReady) {
    Write-Host "[+] lavalink already running" -ForegroundColor Cyan
} else {
    Write-Host "[.] starting lavalink..." -ForegroundColor Cyan

    $javaPath = Get-JavaPath
    $script:LavalinkProcess = Start-Process -FilePath $javaPath `
        -ArgumentList "-jar", "Lavalink.jar" `
        -WorkingDirectory "lavalink" `
        -WindowStyle Hidden `
        -PassThru

    Write-Host "[.] waiting for lavalink" -NoNewline -ForegroundColor Cyan
    $elapsed = 0
    while (-not (Test-LavalinkReady) -and $elapsed -lt $LavalinkTimeout) {
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
        $elapsed++
    }
    Write-Host

    if (Test-LavalinkReady) {
        Write-Host "[+] lavalink ready" -ForegroundColor Cyan
    } else {
        Write-Host "[x] lavalink failed to start within $LavalinkTimeout seconds" -ForegroundColor Red
        Write-Host "    check lavalink\logs\ for details."
        Stop-LavalinkIfStarted
        exit 1
    }
}

Write-Host

# Start the bot
Write-Host "[.] starting jill..." -ForegroundColor Magenta
Write-Host
& $VenvPython bot.py

# Cleanup
Stop-LavalinkIfStarted
