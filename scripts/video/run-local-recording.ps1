param(
    [string]$Scene = "dashboard-smoke",
    [string]$NodePath = "C:\tmp\orbit-video-node\node_modules",
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$Headed
)

$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$rawDir = Join-Path $repo "output\video\raw"
$mp4Dir = Join-Path $repo "output\video\mp4"
$logDir = Join-Path $repo "output\video\logs"

New-Item -ItemType Directory -Force -Path $rawDir, $mp4Dir, $logDir | Out-Null

Push-Location $repo
try {
    Write-Host "Preparing demo database..."
    python manage.py migrate --noinput | Out-Host
    python demo.py setup | Out-Host

    $outLog = Join-Path $logDir "runserver.out.log"
    $errLog = Join-Path $logDir "runserver.err.log"
    if (Test-Path $outLog) { Remove-Item $outLog -Force }
    if (Test-Path $errLog) { Remove-Item $errLog -Force }

    Write-Host "Starting Django server at $BaseUrl..."
    $server = Start-Process `
        -FilePath "python" `
        -ArgumentList "manage.py", "runserver", "127.0.0.1:8000", "--noreload" `
        -WorkingDirectory $repo `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -WindowStyle Hidden `
        -PassThru

    try {
        Start-Sleep -Seconds 3
        Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing | Out-Null

        $env:NODE_PATH = $NodePath
        $env:ORBIT_VIDEO_BASE_URL = $BaseUrl

        $args = @("scripts\video\record-orbit-scenes.cjs", "--scene", $Scene)
        if ($Headed) {
            $args += "--headed"
        }

        Write-Host "Recording scene: $Scene"
        node @args | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Playwright recording failed with exit code $LASTEXITCODE"
        }

        $scenes = if ($Scene -eq "all") {
            @("dashboard-smoke", "debug-500", "n-plus-one", "health-safety")
        } else {
            @($Scene)
        }

        foreach ($name in $scenes) {
            $webm = Join-Path $rawDir "$name.webm"
            $mp4 = Join-Path $mp4Dir "$name.mp4"
            if (Test-Path $webm) {
                Write-Host "Converting $name.webm to mp4..."
                ffmpeg -y -i $webm -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -movflags +faststart $mp4 | Out-Host
                if ($LASTEXITCODE -ne 0) {
                    throw "FFmpeg conversion failed for $name with exit code $LASTEXITCODE"
                }
            }
        }

        Write-Host "Done. Outputs:"
        Get-ChildItem $mp4Dir -Filter "*.mp4" | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize
    }
    finally {
        if ($server -and !$server.HasExited) {
            Stop-Process -Id $server.Id -Force
        }
    }
}
finally {
    Pop-Location
}
