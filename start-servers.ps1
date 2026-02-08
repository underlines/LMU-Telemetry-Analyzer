# LMU Telemetry Analyzer - Start Servers
# Starts backend (port 8000) and frontend (port 3000) with logging

$LogDir = "logs"
$BackendLog = "$LogDir\backend.log"
$FrontendLog = "$LogDir\frontend.log"
$PidFile = "$LogDir\.server-pids"

# Create logs directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Clean up old logs
Remove-Item -Path $BackendLog -ErrorAction SilentlyContinue
Remove-Item -Path $FrontendLog -ErrorAction SilentlyContinue
Remove-Item -Path $PidFile -ErrorAction SilentlyContinue

Write-Host "Starting LMU Telemetry servers..."
Write-Host "Logs will be written to: $LogDir"

# Function to write timestamped log
function Write-TimestampedLog {
    param(
        [string]$Message,
        [string]$LogFile
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp $Message" | Out-File -FilePath $LogFile -Append
}

# Start backend server
Write-Host "[1/2] Starting backend server on port 8000..."
$BackendJob = Start-Job -ScriptBlock {
    param($LogPath)
    Set-Location C:\Users\Jan\Documents\GitHub\lmu_telemetry\backend
    & uv run uvicorn app.main:app --reload --port 8000 2>&1 | ForEach-Object {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "$timestamp $_" | Out-File -FilePath $LogPath -Append
    }
} -ArgumentList $BackendLog

# Wait for backend to initialize
Write-Host "Waiting 5 seconds for backend to initialize..."
Start-Sleep -Seconds 5

# Start frontend server
Write-Host "[2/2] Starting frontend server on port 3000..."
$FrontendJob = Start-Job -ScriptBlock {
    param($LogPath)
    Set-Location C:\Users\Jan\Documents\GitHub\lmu_telemetry\frontend
    & npm run dev 2>&1 | ForEach-Object {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "$timestamp $_" | Out-File -FilePath $LogPath -Append
    }
} -ArgumentList $FrontendLog

# Store job IDs for stopping later
@{
    BackendJobId = $BackendJob.Id
    FrontendJobId = $FrontendJob.Id
    StartedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
} | ConvertTo-Json | Out-File -FilePath $PidFile

Write-Host ""
Write-Host "Servers started successfully!"
Write-Host "  - Backend:  http://localhost:8000 (logs: $BackendLog)"
Write-Host "  - Frontend: http://localhost:3000 (logs: $FrontendLog)"
Write-Host ""
Write-Host "Use stop-servers.ps1 to stop both servers."
Write-Host ""

# Show initial log output
Write-Host "Recent backend log output:"
if (Test-Path $BackendLog) {
    Get-Content $BackendLog -Tail 10
}
Write-Host ""
Write-Host "Recent frontend log output:"
if (Test-Path $FrontendLog) {
    Get-Content $FrontendLog -Tail 10
}

Write-Host ""
Write-Host "Servers are running in background. You can close this window."
Write-Host "Use stop-servers.ps1 to stop them."
