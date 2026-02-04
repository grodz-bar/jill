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
            $value = $value -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'  # Strip quotes
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Configuration
$LavalinkPort = if ($env:LAVALINK_PORT) { $env:LAVALINK_PORT } else { 2333 }
$LavalinkTimeout = 90
$LavalinkPassword = if ($env:LAVALINK_PASSWORD) { $env:LAVALINK_PASSWORD } else { "timetomixdrinksandnotchangepasswords" }
$LavalinkJar = "lavalink\Lavalink.jar"
$LavalinkConfig = "lavalink\application.yml"
$VenvPython = "venv\Scripts\python.exe"
# MANAGE_LAVALINK: when true, kill stale on startup and shutdown. Default true.
$ManageLavalink = if ($env:MANAGE_LAVALINK -and $env:MANAGE_LAVALINK.ToLower() -eq "false") { $false } else { $true }
# Check for duplicate ports
$HttpPort = if ($env:HTTP_SERVER_PORT) { $env:HTTP_SERVER_PORT } else { 2334 }
if ($LavalinkPort -eq $HttpPort) {
    Write-Host "[x] LAVALINK_PORT and HTTP_SERVER_PORT are both set to $LavalinkPort" -ForegroundColor Red
    Write-Host "    they must be different - fix in .env"
    exit 1
}

# Track Lavalink process for cleanup
$script:LavalinkProcess = $null

function Test-LavalinkReady {
    # Returns: "ready", "waiting", or "auth_failed"
    try {
        $headers = @{ "Authorization" = $LavalinkPassword }
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$LavalinkPort/version" `
            -Headers $headers -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) { return "ready" }
        return "waiting"
    } catch [System.Net.WebException] {
        $resp = $_.Exception.Response
        if ($resp -and [int]$resp.StatusCode -eq 401) {
            return "auth_failed"
        }
        return "waiting"
    } catch {
        return "waiting"
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
        if ($output -match '(?:version|release)\s*"(\d+)') {
            return [int]$Matches[1]
        }
    } catch {}
    return 0
}

function Stop-LavalinkIfStarted {
    if ($script:LavalinkProcess -and -not $script:LavalinkProcess.HasExited) {
        Write-Host "[.] stopping lavalink..." -ForegroundColor Cyan
        Stop-Process -Id $script:LavalinkProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

function Get-ExcludedPortRanges {
    # Get all Windows reserved/excluded port ranges
    # Returns array of "start-end" strings, or empty array if none/error
    try {
        $output = netsh interface ipv4 show excludedportrange protocol=tcp 2>&1
        if ($LASTEXITCODE -ne 0) {
            return @()
        }
    } catch {
        return @()
    }

    $ranges = @()
    foreach ($line in $output) {
        if ($line -match '^\s*(\d+)\s+(\d+)') {
            $ranges += "$($Matches[1])-$($Matches[2])"
        }
    }
    return $ranges
}

function Test-PortExcluded {
    # Check if port is in any excluded range
    param([int]$Port, [string[]]$Ranges)

    foreach ($range in $Ranges) {
        if ($range -match '^(\d+)-(\d+)$') {
            $start = [int]$Matches[1]
            $end = [int]$Matches[2]
            if ($Port -ge $start -and $Port -le $end) {
                return $true
            }
        }
    }
    return $false
}

# Register cleanup handler
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-LavalinkIfStarted }
trap { Stop-LavalinkIfStarted; break }

# Validation
Write-Host "=== jill startup ===" -ForegroundColor Magenta
Write-Host

# Check venv
if (-not (Test-Path $VenvPython)) {
    Write-Host "[x] virtual environment not found." -ForegroundColor Red
    Write-Host "    run setup-jill-win.bat first."
    exit 1
}
Write-Host "[+] virtual environment found" -ForegroundColor Cyan

# Check venv Python is functional (test pip - if missing, packages won't be installed)
try {
    $null = & $VenvPython -c "import pip" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "pip check failed" }
} catch {
    Write-Host "[x] virtual environment is broken." -ForegroundColor Red
    Write-Host "    run setup-jill-win.bat to fix."
    exit 1
}

# Check Java version
$javaVersion = Get-JavaMajorVersion
if ($javaVersion -eq 0) {
    Write-Host "[x] java 17+ is required for lavalink." -ForegroundColor Red
    Write-Host ""
    Write-Host "    1. download from: https://adoptium.net/temurin/releases/"
    Write-Host "       select: Windows x64, JRE, version 17+, .msi installer"
    Write-Host "    2. run the installer"
    Write-Host "    3. restart this terminal and try again"
    exit 1
}
if ($javaVersion -lt 17) {
    Write-Host "[x] java 17+ required, found java $javaVersion" -ForegroundColor Red
    Write-Host ""
    Write-Host "    1. download from: https://adoptium.net/temurin/releases/"
    Write-Host "       select: Windows x64, JRE, version 17+, .msi installer"
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

# Check if ports are reserved by Windows
$excludedRanges = Get-ExcludedPortRanges
$lavalinkExcluded = Test-PortExcluded $LavalinkPort $excludedRanges
$httpExcluded = Test-PortExcluded $HttpPort $excludedRanges

if ($lavalinkExcluded -or $httpExcluded) {
    $badPorts = @()
    if ($lavalinkExcluded) { $badPorts += $LavalinkPort }
    if ($httpExcluded) { $badPorts += $HttpPort }
    $portList = $badPorts -join ", "
    $portWord = if ($badPorts.Count -eq 1) { "port" } else { "ports" }
    Write-Host "[x] $portWord $portList in reserved range" -ForegroundColor Red
    Write-Host "    currently reserved port ranges:"
    foreach ($range in $excludedRanges) {
        Write-Host "    $range"
    }
    Write-Host "    change $portWord in .env or try restarting your computer"
    exit 1
}

# Validate application.yml matches .env (local installs only)
if (Test-Path $LavalinkConfig) {
    & $VenvPython -c @"
import yaml, os, sys

def clean_env(key, default):
    val = os.environ.get(key, default)
    return val.split(' #')[0].strip() if ' #' in val else val.strip()

env_port = clean_env('LAVALINK_PORT', '2333')
env_pass = clean_env('LAVALINK_PASSWORD', 'timetomixdrinksandnotchangepasswords')

try:
    with open('lavalink/application.yml', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    yml_port = cfg.get('server', {}).get('port')
    yml_pass = cfg.get('lavalink', {}).get('server', {}).get('password')

    if yml_port is not None and str(yml_port).strip() != env_port:
        print(f'\033[91m[x] port mismatch: LAVALINK_PORT={env_port} but application.yml has port: {yml_port}\033[0m')
        print('    fix in .env or lavalink/application.yml')
        sys.exit(1)
    if yml_pass is not None and yml_pass.strip() != env_pass:
        print('\033[91m[x] password mismatch: LAVALINK_PASSWORD does not match application.yml\033[0m')
        print('    fix in .env or lavalink/application.yml')
        sys.exit(1)
except yaml.YAMLError:
    print('\033[93m[!] warning: could not parse application.yml\033[0m')
except FileNotFoundError:
    pass
except Exception:
    pass
"@
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

# Start Lavalink if not running
$lavalinkStatus = Test-LavalinkReady
if ($lavalinkStatus -eq "ready") {
    Write-Host "[+] lavalink already running" -ForegroundColor Cyan
} elseif ($lavalinkStatus -eq "auth_failed") {
    Write-Host "[x] existing lavalink has wrong password" -ForegroundColor Red
    Write-Host "    password in .env must match lavalink/application.yml"
    exit 1
} else {
    # Kill any stale Lavalink process on our port (may be unresponsive zombie)
    # Respects MANAGE_LAVALINK setting - skip if sharing Lavalink with other bots
    if ($ManageLavalink) {
        $existing = Get-NetTCPConnection -LocalPort $LavalinkPort -State Listen -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "[.] killing stale process on port $LavalinkPort..." -ForegroundColor Yellow
            Stop-Process -Id $existing.OwningProcess -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
    }

    Write-Host "[.] starting lavalink..." -ForegroundColor Cyan

    $javaPath = Get-JavaPath
    # JVM args: limit heap to 512MB, use G1GC for better memory management
    $jvmArgs = @("-Xmx512m", "-Xms256m", "-XX:+UseG1GC", "-jar", "Lavalink.jar")
    $script:LavalinkProcess = Start-Process -FilePath $javaPath `
        -ArgumentList $jvmArgs `
        -WorkingDirectory "lavalink" `
        -WindowStyle Hidden `
        -PassThru

    Write-Host "[.] waiting for lavalink" -NoNewline -ForegroundColor Cyan
    $elapsed = 0
    $status = "waiting"
    while ($elapsed -lt $LavalinkTimeout) {
        $status = Test-LavalinkReady
        if ($status -eq "ready") { break }
        if ($status -eq "auth_failed") {
            Write-Host
            Write-Host "[x] lavalink auth failed - check LAVALINK_PASSWORD" -ForegroundColor Red
            Write-Host "    password in .env must match lavalink/application.yml"
            Stop-LavalinkIfStarted
            exit 1
        }
        # Check if process crashed during startup
        if ($script:LavalinkProcess.HasExited) {
            Write-Host
            Write-Host "[x] lavalink crashed during startup (exit code: $($script:LavalinkProcess.ExitCode))" -ForegroundColor Red
            Write-Host "    run manually to see error: cd lavalink && java -jar Lavalink.jar"
            exit 1
        }
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
        $elapsed++
    }
    Write-Host

    if ($status -eq "ready") {
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
