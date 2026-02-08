# LMU Telemetry Analyzer - Stop Servers
# Stops backend and frontend servers started by start-servers.ps1

$LogDir = "logs"
$PidFile = "$LogDir\.server-pids"
$BackendLog = "$LogDir\backend.log"
$FrontendLog = "$LogDir\frontend.log"

Write-Host "Stopping LMU Telemetry servers..."

# Read stored job IDs
if (Test-Path $PidFile) {
    $Pids = Get-Content $PidFile | ConvertFrom-Json
    
    # Stop backend job
    if ($Pids.BackendJobId) {
        Write-Host "Stopping backend server (Job ID: $($Pids.BackendJobId))..."
        $BackendJob = Get-Job -Id $Pids.BackendJobId -ErrorAction SilentlyContinue
        if ($BackendJob) {
            Stop-Job -Id $Pids.BackendJobId -ErrorAction SilentlyContinue
            Remove-Job -Id $Pids.BackendJobId -ErrorAction SilentlyContinue
            Write-Host "  Backend stopped."
        }
    }
    
    # Stop frontend job
    if ($Pids.FrontendJobId) {
        Write-Host "Stopping frontend server (Job ID: $($Pids.FrontendJobId))..."
        $FrontendJob = Get-Job -Id $Pids.FrontendJobId -ErrorAction SilentlyContinue
        if ($FrontendJob) {
            Stop-Job -Id $Pids.FrontendJobId -ErrorAction SilentlyContinue
            Remove-Job -Id $Pids.FrontendJobId -ErrorAction SilentlyContinue
            Write-Host "  Frontend stopped."
        }
    }
    
    # Clean up PID file
    Remove-Item -Path $PidFile -ErrorAction SilentlyContinue
} else {
    Write-Host "No PID file found. Checking for running processes..."
    
    # Try to find and stop by port
    $BackendProcess = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess -First 1
    if ($BackendProcess) {
        Write-Host "Found backend process on port 8000 (PID: $BackendProcess), stopping..."
        Stop-Process -Id $BackendProcess -Force -ErrorAction SilentlyContinue
    }
    
    $FrontendProcess = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess -First 1
    if ($FrontendProcess) {
        Write-Host "Found frontend process on port 3000 (PID: $FrontendProcess), stopping..."
        Stop-Process -Id $FrontendProcess -Force -ErrorAction SilentlyContinue
    }
}

# Also check for any remaining jobs with "uvicorn" or "node" in the command
Write-Host "Checking for any remaining server processes..."
Get-Job | Where-Object { $_.Command -match "uvicorn|npm|node" } | ForEach-Object {
    Write-Host "Stopping orphaned job (ID: $($_.Id))..."
    Stop-Job -Id $_.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $_.Id -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "All servers stopped."
Write-Host "Log files remain at:"
if (Test-Path $BackendLog) {
    Write-Host "  - $BackendLog"
}
if (Test-Path $FrontendLog) {
    Write-Host "  - $FrontendLog"
}
