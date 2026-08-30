[CmdletBinding()]
param(
    [string]$ClientSecrets = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $ClientSecrets) {
    $Downloads = Join-Path $env:USERPROFILE "Downloads"
    $ClientSecrets = Get-ChildItem (Join-Path $Downloads "client_secret_*.json") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

if (-not $ClientSecrets -or -not (Test-Path $ClientSecrets)) {
    throw "OAuth client JSON not found in Downloads."
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
if ($LASTEXITCODE -ne 0) { throw "Could not create the temporary Python environment." }

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Golide = Join-Path $RepoRoot ".venv\Scripts\golide.exe"

& $Python -m pip install --disable-pip-version-check -e ".[production]"
if ($LASTEXITCODE -ne 0) { throw "Dependency setup failed." }

& $Golide oauth-bootstrap ".secrets\youtube-client.json"
if ($LASTEXITCODE -ne 0) { throw "Google authorization did not complete." }

& $Golide youtube-verify
if ($LASTEXITCODE -ne 0) { throw "The authorized Google account does not own the expected YouTube channel." }

$TokenPath = Join-Path $RepoRoot ".secrets\youtube-token.json"
$TokenBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($TokenPath))

$GhCommand = Get-Command gh -ErrorAction SilentlyContinue
if ($GhCommand) {
    $GhExe = $GhCommand.Source
} else {
    Write-Host "Preparing a temporary GitHub helper..." -ForegroundColor Cyan
    $ToolsDir = Join-Path $RepoRoot ".tools"
    New-Item -ItemType Directory -Force $ToolsDir | Out-Null
    $Headers = @{ "User-Agent" = "GOLIDE-OAuth-Bootstrap" }
    $Release = Invoke-RestMethod "https://api.github.com/repos/cli/cli/releases/latest" -Headers $Headers
    $Asset = $Release.assets | Where-Object { $_.name -match "windows_amd64\.zip$" } | Select-Object -First 1
    if (-not $Asset) { throw "Could not locate the temporary GitHub helper." }
    $ZipPath = Join-Path $ToolsDir "gh.zip"
    Invoke-WebRequest $Asset.browser_download_url -Headers $Headers -OutFile $ZipPath
    Expand-Archive $ZipPath -DestinationPath $ToolsDir -Force
    $GhExe = Get-ChildItem $ToolsDir -Filter "gh.exe" -Recurse | Select-Object -First 1 -ExpandProperty FullName
    if (-not $GhExe) { throw "Temporary GitHub helper could not be prepared." }
}

& $GhExe auth status --hostname github.com
if ($LASTEXITCODE -ne 0) {
    Write-Host "GitHub will open once so the cloud secret can be saved." -ForegroundColor Cyan
    & $GhExe auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) { throw "GitHub authorization did not complete." }
}

$TokenBase64 | & $GhExe secret set YOUTUBE_OAUTH_TOKEN_B64 --repo risktacker/golide-content-engine
if ($LASTEXITCODE -ne 0) { throw "Could not save the YouTube token to GitHub." }

& $GhExe variable set GOLIDE_ANALYTICS_ENABLED --repo risktacker/golide-content-engine --body true
if ($LASTEXITCODE -ne 0) { throw "Could not enable daily analytics." }

Write-Host "SUCCESS: YouTube OAuth verified and cloud analytics enabled." -ForegroundColor Green
