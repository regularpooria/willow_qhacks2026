#!/bin/bash

DESKTOP="$HOME/Desktop"
WILLOW_PATH="$DESKTOP/willow"
DOWNLOAD_URL="https://github.com/regularpooria/willow_qhacks2026/releases/download/linux/Willow"

if [ -f "$WILLOW_PATH" ]; then
    echo "Found willow on Desktop, running it..."
    chmod +x "$WILLOW_PATH"
    "$WILLOW_PATH"
else
    echo "Willow not found on Desktop, downloading..."
    curl -L -o "$WILLOW_PATH" "$DOWNLOAD_URL"
    
    if [ $? -eq 0 ]; then
        echo "Download successful, running willow..."
        chmod +x "$WILLOW_PATH"
        "$WILLOW_PATH"
    else
        echo "Failed to download willow"
        exit 1
    fi
fi
