[CmdletBinding()]
param(
    [string]$ClientSecrets = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $ClientSecrets) {
    $ClientSecrets = Get-ChildItem "$HOME\Downloads\client_secret_*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

if (-not $ClientSecrets -or -not (Test-Path $ClientSecrets)) {
    throw "OAuth client JSON not found. Download it to Downloads or pass -ClientSecrets C:\path\client_secret.json"
}

New-Item -ItemType Directory -Force ".secrets" | Out-Null
Copy-Item $ClientSecrets ".secrets\youtube-client.json" -Force

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv .venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv .venv
} else {
    throw "Python 3.11 or newer is required."
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Golide = Join-Path $RepoRoot ".venv\Scripts\golide.exe"

& $Python -m pip install --disable-pip-version-check -e ".[production]"
& $Golide oauth-bootstrap ".secrets\youtube-client.json"
& $Golide youtube-verify

$TokenPath = Join-Path $RepoRoot ".secrets\youtube-token.json"
$TokenBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($TokenPath))

if (Get-Command gh -ErrorAction SilentlyContinue) {
    & gh auth status | Out-Host
    & gh secret set YOUTUBE_OAUTH_TOKEN_B64 --repo risktacker/golide-content-engine --body $TokenBase64
    & gh variable set GOLIDE_ANALYTICS_ENABLED --repo risktacker/golide-content-engine --body true
    Write-Host "YouTube OAuth verified and daily analytics enabled." -ForegroundColor Green
} else {
    Set-Clipboard $TokenBase64
    Write-Host "YouTube OAuth verified. The encoded token is on your clipboard." -ForegroundColor Yellow
    Write-Host "GitHub CLI was not found; add the clipboard value as repository secret YOUTUBE_OAUTH_TOKEN_B64."
}
