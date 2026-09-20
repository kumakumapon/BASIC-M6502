param([switch]$Emulators, [switch]$Tests)
$ErrorActionPreference = 'Stop'
$toolArgs = @("$PSScriptRoot/scripts/setup_tools.py")
if ($Emulators) { $toolArgs += '--emulators' }
if ($Tests) { $toolArgs += '--tests' }
python @toolArgs
if ($LASTEXITCODE -ne 0) { throw 'Tool setup failed' }
