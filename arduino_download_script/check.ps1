$Desktop = [Environment]::GetFolderPath("Desktop")
$WillowPath = Join-Path $Desktop "willow.exe"
$DownloadUrl = "YOUR_DOWNLOAD_LINK_HERE"

if (Test-Path $WillowPath) {
    Write-Host "Found willow.exe on Desktop, running it..."
    Start-Process -FilePath $WillowPath
} else {
    Write-Host "Willow.exe not found on Desktop, downloading..."
    try {
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $WillowPath
        Write-Host "Download successful, running willow..."
        Start-Process -FilePath $WillowPath
    } catch {
        Write-Host "Failed to download willow.exe: $_"
        exit 1
    }
}
