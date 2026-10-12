# Starts the Vite dev server. /api requests are proxied to the backend.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1 [-ApiPort 8000]
param([int]$ApiPort = 8000)

$ErrorActionPreference = 'Stop'
$frontend = Join-Path (Split-Path -Parent $PSScriptRoot) 'frontend'
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) { throw 'node_modules not found. Run .\scripts\setup.ps1 first.' }

Set-Location $frontend
$env:API_TARGET = "http://127.0.0.1:$ApiPort"
Write-Host "Frontend: http://localhost:5173  (proxying /api to $env:API_TARGET)" -ForegroundColor Green
npm run dev
