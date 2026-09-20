# ba PowerShell Wrapper for Windows
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaBashScript = Join-Path (Split-Path -Parent $ScriptDir) "scripts\ba.sh"

$gitBash = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $gitBash)) {
    $localGit = "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe"
    if (Test-Path $localGit) {
        $gitBash = $localGit
    } else {
        $gitCmd = Get-Command git -ErrorAction SilentlyContinue
        if ($gitCmd) {
            $candidate = Join-Path (Split-Path -Parent (Split-Path -Parent $gitCmd.Source)) "bin\bash.exe"
            if (Test-Path $candidate) { $gitBash = $candidate }
        }
    }
}

if (Test-Path $gitBash) {
    & $gitBash $BaBashScript @args
} else {
    & bash $BaBashScript @args
}
exit $LASTEXITCODE
