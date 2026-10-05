$ErrorActionPreference = 'Stop'
$taskProject = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskProject
uv sync --frozen
if ($LASTEXITCODE -ne 0) { throw 'Python installation failed' }
if (-not (Test-Path 'apps/dashboard/node_modules/next')) {
    Push-Location apps/dashboard
    try { npm ci; if ($LASTEXITCODE -ne 0) { throw 'Dashboard installation failed' } }
    finally { Pop-Location }
}
uv run python scripts/run_local.py --demo
