$ErrorActionPreference = "Stop"

function Write-Info([string]$Message) {
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Success([string]$Message) {
    Write-Host $Message -ForegroundColor Green
}

function Write-Failure([string]$Message) {
    Write-Host $Message -ForegroundColor Red
}

function Remove-IfExists([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvCandidates = @()

if ($env:VIRTUAL_ENV) {
    $venvCandidates += (
        Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
    )
}

$venvCandidates += @(
    (Join-Path $ScriptDir "venv\Scripts\python.exe"),
    (Join-Path $ScriptDir ".venv\Scripts\python.exe"),
    (Join-Path $ScriptDir "..\venv\Scripts\python.exe"),
    (Join-Path $ScriptDir "..\.venv\Scripts\python.exe")
)

$PythonExe = $null
foreach ($candidate in $venvCandidates) {
    if (Test-Path -LiteralPath $candidate) {
        $PythonExe = $candidate
        break
    }
}

if ($PythonExe) {
    Write-Info "Using Python: $PythonExe"
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        Write-Failure "Python was not found."
        Write-Host "Activate or create a virtual environment first."
        exit 1
    }

    Write-Info "Virtual environment not found. Using Python from PATH."
    $PythonExe = $pythonCommand.Source
}

Write-Info "Checking pip..."
& $PythonExe -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Failure "pip is not available for $PythonExe."
    exit $LASTEXITCODE
}

Write-Info "Checking build dependency: hatchling>=1.27..."
& $PythonExe -c "import hatchling"
if ($LASTEXITCODE -ne 0) {
    Write-Failure "hatchling>=1.27 is required."
    Write-Host 'Fix: python -m pip install "hatchling>=1.27"'
    exit 1
}

Write-Info "Uninstalling the previous BrasidataCenter installation..."
& $PythonExe -m pip uninstall -y brasidatacenter
if ($LASTEXITCODE -ne 0) {
    Write-Failure "Failed to uninstall brasidatacenter."
    exit $LASTEXITCODE
}

Write-Info "Removing build artifacts..."
Remove-IfExists (Join-Path $ScriptDir "build")
Remove-IfExists (Join-Path $ScriptDir "dist")
Remove-IfExists (Join-Path $ScriptDir "src\brasidatacenter.egg-info")
Remove-IfExists (Join-Path $ScriptDir "src\brasidatacenter\__pycache__")

Write-Info "Installing BrasidataCenter in editable mode..."
& $PythonExe -m pip install -e $ScriptDir --no-build-isolation
if ($LASTEXITCODE -ne 0) {
    Write-Failure "Installation failed."
    exit $LASTEXITCODE
}

Write-Success "BrasidataCenter was reinstalled successfully."
