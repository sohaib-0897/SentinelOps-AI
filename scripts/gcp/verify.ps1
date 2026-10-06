[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-z][a-z0-9-]{4,28}[a-z0-9]$')][string]$ProjectId,
    [string]$Region = 'us-central1',
    [ValidateSet('production','staging')][string]$Environment = 'production',
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
$TaskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$Arguments = @('run','--extra','gcp','python','-m','scripts.gcp.control','verify','--project-id',$ProjectId,'--region',$Region,'--environment',$Environment)
if ($Execute) { $Arguments += '--execute' }
Push-Location $TaskRoot
try {
    & uv @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'SentinelOps cloud command failed; no following step will run.' }
} finally { Pop-Location }
