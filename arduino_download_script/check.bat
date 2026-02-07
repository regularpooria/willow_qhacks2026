@echo off
setlocal

set "DESKTOP=%USERPROFILE%\Desktop"
set "WILLOW_PATH=%DESKTOP%\willow.exe"
set "DOWNLOAD_URL=YOUR_DOWNLOAD_LINK_HERE"

if exist "%WILLOW_PATH%" (
    echo Found willow.exe on Desktop, running it...
    start "" "%WILLOW_PATH%"
) else (
    echo Willow.exe not found on Desktop, downloading...
    curl -L -o "%WILLOW_PATH%" "%DOWNLOAD_URL%"
    
    if %errorlevel% equ 0 (
        echo Download successful, running willow...
        start "" "%WILLOW_PATH%"
    ) else (
        echo Failed to download willow.exe
        exit /b 1
    )
)
