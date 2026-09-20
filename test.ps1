param([switch]$Emulators)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    python scripts/build.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
    python -m unittest discover -s tests -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'CPU/translation tests failed' }
    if ($Emulators) {
        python scripts/test_mesen.py
        if ($LASTEXITCODE -ne 0) { throw 'Mesen tests failed' }
        python scripts/test_fceux.py
        if ($LASTEXITCODE -ne 0) { throw 'FCEUX tests failed' }
    }
} finally { Pop-Location }
