$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
try {
    $taskStatus = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/status' -TimeoutSec 3
    if ($taskStatus.stats.scenes) {
        Write-Host 'DialogueMatch is already running at http://127.0.0.1:8765'
        return
    }
} catch { }
if (-not (Test-Path -LiteralPath 'data/dialoguematch.sqlite')) {
    python -m dialoguematch build
    if ($LASTEXITCODE -ne 0) { throw 'Corpus build failed.' }
    if (Test-Path -LiteralPath 'data/dialoguematch.vectors.npy') {
        python -m dialoguematch build-gap
    }
}
if (-not (Test-Path -LiteralPath 'data/dialoguematch.context.sqlite')) {
    python -m dialoguematch build-context
}
Write-Host 'Starting DialogueMatch: verifying search indexes and loading local encoders...'
Write-Host 'Wait for the "DialogueMatch is running" message, then open http://127.0.0.1:8765. Press Ctrl+C to stop.'
python -m dialoguematch serve
