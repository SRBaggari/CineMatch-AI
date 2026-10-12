# One-time setup: Python virtual environment + backend packages + frontend packages.
# Usage (from the project root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

Write-Host '== Checking prerequisites ==' -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python 3.10+ is required (https://www.python.org/downloads/).' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Node.js 20+ is required (https://nodejs.org/).' }
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 or newer is required.' }
Write-Host ("Python: " + (python --version))
Write-Host ("Node:   " + (node --version))

Write-Host '== Backend: creating virtual environment ==' -ForegroundColor Cyan
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) { python -m venv (Join-Path $backend '.venv') }
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $backend 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install failed.' }

Write-Host '== Frontend: installing npm packages ==' -ForegroundColor Cyan
Push-Location $frontend
try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
} finally {
    Pop-Location
}

Write-Host ''
Write-Host 'Setup complete. Start the app with:' -ForegroundColor Green
Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\start-all.ps1'
