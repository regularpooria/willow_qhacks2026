$Desktop     = [Environment]::GetFolderPath("Desktop")
$WillowPath  = Join-Path $Desktop "willow.exe"
$DownloadUrl = "https://github.com/regularpooria/willow_qhacks2026/releases/download/windows/Willow.exe"

if (Test-Path $WillowPath) {
    Write-Host "Found willow.exe on Desktop, running it..."
    Start-Process $WillowPath
}
else {
    Write-Host "Willow.exe not found on Desktop, downloading..."

    try {
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $WillowPath -UseBasicParsing
        Write-Host "Download successful, running willow..."
        Start-Process $WillowPath
    }
    catch {
        Write-Host "Failed to download willow.exe"
        exit 1
    }
}
