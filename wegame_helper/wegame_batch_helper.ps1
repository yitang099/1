# WeGameTQ batch helper
param(
    [string]$SoftwareDir = "",
    [int]$WaitSeconds = 5,
    [switch]$AutoStart,
    [string]$StartExe = "WeGametq.exe"
)

$helperDir = $PSScriptRoot
$cleanScript = Join-Path $helperDir "clean_cef_cache.ps1"

if ([string]::IsNullOrWhiteSpace($SoftwareDir)) {
    $SoftwareDir = Read-Host "Enter WeGameTQ folder path"
}
$SoftwareDir = $SoftwareDir.Trim().Trim('"')

if (-not (Test-Path (Join-Path $SoftwareDir $StartExe))) {
    Write-Host "[ERROR] Not found: $(Join-Path $SoftwareDir $StartExe)" -ForegroundColor Red
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " WeGameTQ Batch Helper" -ForegroundColor Cyan
Write-Host (" Target: " + $SoftwareDir) -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

powershell -ExecutionPolicy Bypass -File $cleanScript -SoftwareDir $SoftwareDir
Start-Sleep -Seconds $WaitSeconds

if ($AutoStart) {
    $exePath = Join-Path $SoftwareDir $StartExe
    Write-Host ("Starting: " + $exePath) -ForegroundColor Cyan
    Start-Process -FilePath $exePath -WorkingDirectory $SoftwareDir
} else {
    $ans = Read-Host "Start WeGametq now? Y/N"
    if ($ans -match "^[Yy]") {
        $exePath = Join-Path $SoftwareDir $StartExe
        Start-Process -FilePath $exePath -WorkingDirectory $SoftwareDir
    }
}

Write-Host ""
Write-Host "Tips:" -ForegroundColor Yellow
Write-Host "  - Run after every 10-15 accounts"
Write-Host "  - Switch network IP before next batch"
Write-Host "  - Set interval 15-30 sec in software"
