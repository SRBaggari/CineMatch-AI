# Opens the backend and frontend in two separate PowerShell windows.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\start-all.ps1 [-Port 8000]
param([int]$Port = 8000)

$backendScript = Join-Path $PSScriptRoot 'start-backend.ps1'
$frontendScript = Join-Path $PSScriptRoot 'start-frontend.ps1'

Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', "`"$backendScript`"", '-Port', $Port
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', "`"$frontendScript`"", '-ApiPort', $Port

Write-Host 'Backend and frontend are starting in new windows.' -ForegroundColor Green
Write-Host 'Open http://localhost:5173 in your browser.'
