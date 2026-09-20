[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ZenHome,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ZenArgs
)

$ErrorActionPreference = 'Stop'
$ZenArgs = @($ZenArgs | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
$env:ZEN_HOME = (Resolve-Path $ZenHome).Path
$repo = Join-Path $env:ZEN_HOME 'repo\ZEN-MA2-Agent'
$launcher = Join-Path $repo 'launcher\zen_portable_launcher.py'
$privateProviderFile = Join-Path $env:ZEN_HOME 'secrets\providers.private.env'
if (-not (Test-Path (Join-Path $repo '.git'))) { throw "Portable Git working copy is missing: $repo" }

function Get-ZenPython {
    $portable = Join-Path $env:ZEN_HOME 'runtime\windows\venv\Scripts\python.exe'
    if (Test-Path $portable) { return $portable }
    foreach ($candidate in @('py.exe', 'python.exe')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    throw 'Python is required to bootstrap the USB runtime. Install Python on this host or place a portable runtime under runtime\windows\.'
}

function Invoke-ZenLauncher {
    param([string[]]$Arguments)
    $python = Get-ZenPython
    $env:PYTHONPATH = $repo
    $raw = & $python $launcher @Arguments
    if ($LASTEXITCODE -ne 0) { throw "ZEN launcher failed: $($raw -join [Environment]::NewLine)" }
    $text = $raw -join [Environment]::NewLine
    try { return $text | ConvertFrom-Json } catch { throw "ZEN launcher returned invalid status: $text" }
}

function Show-ZenHeader {
    Clear-Host
    Write-Host ''
    Write-Host 'ZEN MA2 AGENT' -ForegroundColor Cyan
    Write-Host "ZEN_HOME: $env:ZEN_HOME" -ForegroundColor DarkGray
    Write-Host ''
}

function Show-Preflight {
    Write-Host 'Checking portable Git...' -ForegroundColor DarkGray
    $git = Invoke-ZenLauncher @('--update')
    Write-Host "Git: $($git.GIT_SYNC_STATUS)  Branch: $($git.branch)" -ForegroundColor Gray

    Write-Host 'Checking MA2 TCP connectivity...' -ForegroundColor DarkGray
    $ma2 = Invoke-ZenLauncher @('--ma2-connectivity')
    $ma2Color = if ($ma2.MA2_CONNECTIVITY -eq 'TCP_REACHABLE') { 'Green' } else { 'Yellow' }
    Write-Host "MA2: $($ma2.MA2_CONNECTIVITY) ($($ma2.host):$($ma2.port))" -ForegroundColor $ma2Color

    Write-Host 'Checking autonomous Designer provider...' -ForegroundColor DarkGray
    $provider = Invoke-ZenLauncher @('--provider-self-test')
    if ($provider.AUTONOMOUS_DESIGNER_AVAILABLE -eq 'YES') {
        Write-Host "AUTONOMOUS DESIGNER: READY - slot $($provider.provider_slot), $($provider.provider_type) / $($provider.model)" -ForegroundColor Green
    } else {
        $configured = @($provider.slots | Where-Object { $_.base_url_configured -and $_.model -and (-not $_.api_key_required -or $_.api_key_configured) })
        if ($configured.Count -eq 0) {
            Write-Host 'AUTONOMOUS DESIGNER: NOT CONFIGURED' -ForegroundColor Yellow
        } else {
            Write-Host "AUTONOMOUS DESIGNER: UNAVAILABLE - $($provider.reason)" -ForegroundColor Yellow
        }
    }
    Write-Host ''
    return @{ Git = $git; MA2 = $ma2; Provider = $provider }
}

function Start-ZenRuntime {
    Write-Host 'Starting ZEN...' -ForegroundColor Cyan
    Set-Location $repo
    $python = Get-ZenPython
    $env:PYTHONPATH = $repo
    & $python (Join-Path $repo 'main.py')
    if ($LASTEXITCODE -ne 0) { Write-Host "ZEN exited with code $LASTEXITCODE." -ForegroundColor Yellow }
    else { Write-Host 'ZEN closed.' -ForegroundColor DarkGray }
}

function Open-ProviderSetup {
    $parent = Split-Path -Parent $privateProviderFile
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    if (-not (Test-Path $privateProviderFile)) {
        @(
            '# USB-local private provider configuration. Never commit this file.',
            '# Default here is a lightweight local fallback, not the primary artistic brain.',
            '# See config/providers.private.env.example for local-only setup or',
            '# config/providers.free_pool.env.example for the multi-cloud free-first pool.',
            '# Edit ZEN_PROVIDER_1_MODEL to match the exact local server model id.',
            'ZEN_PROVIDER_MODE=PRIMARY_ONLY',
            'ZEN_PROVIDER_SLOT_COUNT=3',
            'ZEN_PROVIDER_PARALLELISM=1',
            'ZEN_PROVIDER_PARALLEL_ROLES=',
            '',
            'ZEN_PROVIDER_1_TYPE=OPENAI_COMPATIBLE_LOCAL',
            'ZEN_PROVIDER_1_MODEL=Qwen3-4B-Q4_K_M',
            'ZEN_PROVIDER_1_BASE_URL=http://127.0.0.1:8080/v1',
            'ZEN_PROVIDER_1_API_KEY=',
            'ZEN_PROVIDER_1_ROLES=',
            'ZEN_PROVIDER_1_PRIORITY=100',
            'ZEN_PROVIDER_1_COST_CLASS=LOCAL',
            'ZEN_PROVIDER_1_RESPONSE_FORMAT=JSON_OBJECT',
            'ZEN_PROVIDER_1_TIMEOUT_SECONDS=120',
            '',
            'ZEN_PROVIDER_2_TYPE=', 'ZEN_PROVIDER_2_MODEL=', 'ZEN_PROVIDER_2_BASE_URL=', 'ZEN_PROVIDER_2_API_KEY=',
            'ZEN_PROVIDER_3_TYPE=', 'ZEN_PROVIDER_3_MODEL=', 'ZEN_PROVIDER_3_BASE_URL=', 'ZEN_PROVIDER_3_API_KEY='
        ) | Set-Content -LiteralPath $privateProviderFile -Encoding utf8
    }
    Start-Process notepad.exe -ArgumentList ('"' + $privateProviderFile + '"')
    Write-Host "Opened USB-local provider setup: $privateProviderFile" -ForegroundColor Cyan
}

if ($ZenArgs -contains '--bootstrap-runtime') {
    $hostPython = Get-ZenPython
    $venv = Join-Path $env:ZEN_HOME 'runtime\windows\venv'
    if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) { & $hostPython -m venv $venv }
    $portablePython = Join-Path $venv 'Scripts\python.exe'
    & $portablePython -m pip install --upgrade pip
    & $portablePython -m pip install -r (Join-Path $repo 'requirements.txt')
    Write-Host "ZEN USB runtime ready: $portablePython"
    exit 0
}

if ($ZenArgs.Count -gt 0) {
    $python = Get-ZenPython
    $env:PYTHONPATH = $repo
    & $python $launcher @ZenArgs
    exit $LASTEXITCODE
}

try {
    Show-ZenHeader
    $state = Show-Preflight
    $providerAvailability = [string]$state.Provider.AUTONOMOUS_DESIGNER_AVAILABLE
    Write-Host "Provider preflight result: $providerAvailability" -ForegroundColor DarkGray
    if ($providerAvailability -eq 'YES') {
        Start-ZenRuntime
    } else {
        do {
            Write-Host 'ZEN MA2 AGENT'
            Write-Host '[1] Start ZEN'
            Write-Host '[2] Provider Setup'
            Write-Host '[3] Provider Self-Test'
            Write-Host '[4] Git Update'
            Write-Host '[5] Git Status'
            Write-Host '[6] Exit'
            $choice = Read-Host 'Choose'
            switch ($choice) {
                '1' { Start-ZenRuntime }
                '2' { Open-ProviderSetup }
                '3' { Invoke-ZenLauncher @('--provider-self-test') | ConvertTo-Json -Depth 5; Write-Host '' }
                '4' { Invoke-ZenLauncher @('--update') | ConvertTo-Json -Depth 5; Write-Host '' }
                '5' { Invoke-ZenLauncher @('--git-status') | ConvertTo-Json -Depth 5; Write-Host '' }
                '6' { break }
                default { Write-Host 'Choose 1-6.' -ForegroundColor Yellow }
            }
        } while ($choice -ne '6')
    }
} catch {
    Write-Host ''
    Write-Host "ZEN startup error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Write-Host ''
    Read-Host 'Press Enter to close'
}
