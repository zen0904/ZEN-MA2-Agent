[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$WorkerId,

    [string]$Python = "python",

    [string]$BindHost = "127.0.0.1",

    [int]$Port = 8878,

    [switch]$AllowRemote
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path $RepoRoot).Path

if (-not (Test-Path (Join-Path $repo "zen_ma2_agent"))) {
    throw "ZEN package not found under: $repo"
}

$argsList = @(
    "-m", "zen_ma2_agent.worker.cli",
    "--worker-id", $WorkerId,
    "--host", $BindHost,
    "--port", [string]$Port
)

if ($AllowRemote) {
    $argsList += "--allow-remote"
}

Set-Location $repo
& $Python @argsList
exit $LASTEXITCODE
