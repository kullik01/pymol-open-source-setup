<#
.SYNOPSIS
    Copy the authenticated gh credential into GH_TOKEN for child processes.

.DESCRIPTION
    Reads the credential from gh's authenticated credential store without
    displaying it, and sets GH_TOKEN only for this PowerShell process and its
    child processes. Dot-source this script when the current shell must retain
    the variable. The credential must already be valid in this same execution
    context.
#>

$ghPath = $env:CODEV_GH_PATH
if (-not $ghPath) {
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($gh) {
        $ghPath = $gh.Source
    }
    else {
        $ghPath = 'C:\Program Files\GitHub CLI\gh.exe'
    }
}

if (-not (Test-Path -LiteralPath $ghPath)) {
    throw "gh CLI was not found. Install it or set CODEV_GH_PATH."
}

$token = & $ghPath auth token --hostname github.com 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($token)) {
    throw "gh is not authenticated in this process context. Run: gh auth login --web"
}

$env:GH_TOKEN = $token.Trim()
Write-Output "GH_TOKEN is set for this PowerShell process and child processes."
