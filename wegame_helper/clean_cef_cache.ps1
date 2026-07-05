# WeGameTQ CEF cache cleaner
param(
    [string]$SoftwareDir = $PSScriptRoot
)

$ErrorActionPreference = "SilentlyContinue"

if (-not (Test-Path $SoftwareDir)) {
    Write-Host "[ERROR] Directory not found: $SoftwareDir" -ForegroundColor Red
    exit 1
}

$cefDir = Join-Path $SoftwareDir "CEFLib"
$targets = @(
    (Join-Path $cefDir "GPUCache"),
    (Join-Path $cefDir "DawnCache"),
    (Join-Path $cefDir "old_GPUCache_002"),
    (Join-Path $cefDir "old_DawnCache_002"),
    (Join-Path $cefDir "Extension State"),
    (Join-Path $cefDir "Web Data"),
    (Join-Path $cefDir "Web Data-journal"),
    (Join-Path $cefDir "debug.log"),
    (Join-Path $cefDir "log.txt")
)

$procs = @(
    "WeGametq",
    "WeGametq.vmp",
    "data提取6",
    "提data打码软件",
    "FBrowserCEF3Subprocess",
    "浏览器测试"
)

Write-Host "=== Stop WeGameTQ processes ===" -ForegroundColor Cyan
foreach ($name in $procs) {
    Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host ("  kill: " + $_.ProcessName + " PID " + $_.Id)
        Stop-Process -Id $_.Id -Force
    }
}
Start-Sleep -Seconds 2

Write-Host "=== Clean CEF cache ===" -ForegroundColor Cyan
$removed = 0
foreach ($path in $targets) {
    if (Test-Path $path) {
        if ((Get-Item $path).PSIsContainer) {
            Remove-Item $path -Recurse -Force
        } else {
            Remove-Item $path -Force
        }
        if (-not (Test-Path $path)) {
            Write-Host ("  removed: " + $path) -ForegroundColor Green
            $removed++
        } else {
            Write-Host ("  failed: " + $path) -ForegroundColor Yellow
        }
    }
}

Write-Host ("Done. cleaned " + $removed + " item(s).") -ForegroundColor Green
