# Starts the FastAPI backend with auto-reload.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1 [-Port 8000]
param([int]$Port = 8000)

$ErrorActionPreference = 'Stop'
$backend = Join-Path (Split-Path -Parent $PSScriptRoot) 'backend'
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) { throw 'Virtual environment not found. Run .\scripts\setup.ps1 first.' }

Set-Location $backend
Write-Host "Backend: http://127.0.0.1:$Port   API docs: http://127.0.0.1:$Port/docs" -ForegroundColor Green
& $venvPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
