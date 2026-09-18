[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$ZenHome,

    [string]$Python = "python",

    [string[]]$Worker = @(),

    [int]$OperatorPort = 8876,

    [int]$BridgePort = 8877
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path $RepoRoot).Path
$env:ZEN_HOME = $ZenHome
$main = Join-Path $repo "main.py"

if (-not (Test-Path $main)) {
    throw "ZEN main.py not found: $main"
}

$argsList = @(
    $main,
    "--operator-host", "127.0.0.1",
    "--operator-port", [string]$OperatorPort,
    "--bridge-host", "127.0.0.1",
    "--bridge-port", [string]$BridgePort
)

foreach ($endpoint in $Worker) {
    if (-not [string]::IsNullOrWhiteSpace($endpoint)) {
        $argsList += @("--worker", $endpoint)
    }
}

Set-Location $repo
& $Python @argsList
exit $LASTEXITCODE
