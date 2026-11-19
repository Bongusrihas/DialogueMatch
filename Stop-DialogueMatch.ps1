$ErrorActionPreference = 'Stop'
$taskPidFile = Join-Path $PSScriptRoot 'data\server.pid'
if (Test-Path -LiteralPath $taskPidFile) {
    $taskServerId = [int](Get-Content -LiteralPath $taskPidFile)
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$taskServerId" -ErrorAction SilentlyContinue
    if ($taskProcess -and $taskProcess.CommandLine -match '-m\s+dialoguematch\s+serve') {
        Stop-Process -Id $taskServerId
        Write-Host 'DialogueMatch stopped.'
    }
    Remove-Item -LiteralPath $taskPidFile
} else {
    Write-Host 'No background server recorded. For a terminal launch, press Ctrl+C in that terminal.'
}
