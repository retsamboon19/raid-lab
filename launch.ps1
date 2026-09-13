param([switch]$CreateShortcut, [switch]$PrepareOnly, [switch]$NoBrowser, [ValidateRange(1024,65535)][int]$Port=8766)
$ErrorActionPreference = 'Stop'

$packageRoot = $PSScriptRoot
$runtimeDirectory = Join-Path $packageRoot 'runtime'
$pythonExecutable = Join-Path $runtimeDirectory 'python.exe'
$appDirectory = Join-Path $packageRoot 'tools\raid-lab'
$serverScript = Join-Path $appDirectory 'server.py'
$runtimeUrl = 'https://www.python.org/ftp/python/3.14.6/python-3.14.6-embed-amd64.zip'
$runtimeSha256 = 'df901e84a896ff1ee720ad03377e0c8d8c2244fda79808aeeaff6316df1cb75c'
$raidLabUrl = "http://127.0.0.1:$Port"
$setupLock = $null

function Initialize-BrowserRuntime {
    $destination = Join-Path $appDirectory '.browser-runtime'
    if (Test-Path -LiteralPath (Join-Path $destination 'websocket\__init__.py')) { return }
    Write-Host 'Preparing browser sign-in support...'
    $archive = Join-Path ([IO.Path]::GetTempPath()) ('raid-lab-browser-' + [guid]::NewGuid().ToString('N') + '.zip')
    try {
        Invoke-WebRequest -Uri 'https://files.pythonhosted.org/packages/34/db/b10e48aa8fff7407e67470363eac595018441cf32d5e1001567a7aeba5d2/websocket_client-1.9.0-py3-none-any.whl' -OutFile $archive -UseBasicParsing
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'af248a825037ef591efbf6ed20cc5faa03d3b47b9e5a2230a529eeee1c1fc3ef') { throw 'Browser dependency failed its integrity check. Run setup again.' }
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        Expand-Archive -LiteralPath $archive -DestinationPath $destination -Force
    } finally { if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force } }
}

function Initialize-RaidLabRuntime {
    if (Test-Path -LiteralPath $pythonExecutable) { return }

    Write-Host 'Raid Lab is preparing its private Python runtime for first use...'
    $downloadPath = Join-Path ([IO.Path]::GetTempPath()) ('raid-lab-python-' + [guid]::NewGuid().ToString('N') + '.zip')
    try {
        Invoke-WebRequest -Uri $runtimeUrl -OutFile $downloadPath -UseBasicParsing
        $actualHash = (Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $runtimeSha256) { throw 'The downloaded Python runtime failed its integrity check.' }
        New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
        Expand-Archive -LiteralPath $downloadPath -DestinationPath $runtimeDirectory -Force
    } finally {
        if (Test-Path -LiteralPath $downloadPath) { Remove-Item -LiteralPath $downloadPath -Force }
    }

    $pathFile = Get-ChildItem -LiteralPath $runtimeDirectory -Filter 'python*._pth' | Select-Object -First 1
    if (-not $pathFile) { throw 'The private Python runtime is incomplete.' }
    $pathLines = Get-Content -LiteralPath $pathFile.FullName
    if ('..\tools\raid-lab' -notin $pathLines) {
        Add-Content -LiteralPath $pathFile.FullName -Value "`n..\tools\raid-lab`n..\tools\nikke-team-builder"
    }
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Raid Lab requires 64-bit Windows.' }
    if (-not (Test-Path -LiteralPath $serverScript)) { throw 'The Raid Lab application files are incomplete.' }
    try { $setupLock = [IO.File]::Open((Join-Path $packageRoot '.setup.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch { throw 'Setup is already running in this folder. Wait for that window to finish.' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Initialize-RaidLabRuntime
    Initialize-BrowserRuntime
    & $pythonExecutable -c "import core, browser_login; print('Raid Lab is ready.')"
    if ($LASTEXITCODE -ne 0) { throw 'Application files are missing. Extract the complete ZIP and try again.' }
    if ($PrepareOnly) { return }
    if ($CreateShortcut) {
        $desktop = [Environment]::GetFolderPath('Desktop')
        if ($desktop -and (Test-Path -LiteralPath $desktop)) {
            $shell = New-Object -ComObject WScript.Shell
            $shortcut = $shell.CreateShortcut((Join-Path $desktop 'Raid Lab.lnk'))
            $shortcut.TargetPath = Join-Path $packageRoot 'Start Raid Lab.bat'
            $shortcut.WorkingDirectory = $packageRoot
            $shortcut.Description = 'Open Raid Lab'
            $shortcut.Save()
        }
    }

    $raidLabReady = $false
    try {
        $health = Invoke-RestMethod -Uri "$raidLabUrl/api/health" -TimeoutSec 2
        $raidLabReady = $health.app -eq 'Raid Lab'
    } catch { }

    if (-not $raidLabReady) {
        $stdout = Join-Path $appDirectory 'server.log'
        $stderr = Join-Path $appDirectory 'server-error.log'
        Start-Process -FilePath $pythonExecutable -ArgumentList @('"' + $serverScript + '"','--port',"$Port") -WorkingDirectory $appDirectory -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            Start-Sleep -Milliseconds 300
            try {
                $health = Invoke-RestMethod -Uri "$raidLabUrl/api/health" -TimeoutSec 1
                if ($health.app -eq 'Raid Lab') { $raidLabReady = $true; break }
            } catch { }
        }
    }

    if (-not $raidLabReady) { throw 'Raid Lab could not start. Check tools\raid-lab\server-error.log.' }
    if (-not $NoBrowser) { Start-Process $raidLabUrl }
    Write-Host "Ready: $raidLabUrl"
} catch {
    Write-Error $_.Exception.Message
    exit 1
} finally {
    if ($setupLock) { $setupLock.Dispose() }
}
