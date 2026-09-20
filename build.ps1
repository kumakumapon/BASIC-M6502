param([string]$Cc65Bin = "$PSScriptRoot/.tools/cc65/bin")
$ErrorActionPreference = 'Stop'
$env:CC65_BIN = $Cc65Bin
python "$PSScriptRoot/scripts/build.py"
if ($LASTEXITCODE -ne 0) { throw 'NES build failed' }
