#!/bin/bash
# Simple setup script for Linux/Mac
pip install virtualenv
virtualenv venv
source venv/bin/activate
sudo dnf install portaudio-devel python3-devel
pip install -r requirements.txt
export PLAYWRIGHT_BROWSERS_PATH=0
playwright install chromium
rm -rf dist
rm -rf build
pyinstaller --noconfirm --onefile --windowed --icon "favicon.ico" --name "Willow" --add-data "records:records/" --add-data "public:public/" --add-data "web:web/" --add-data ".env:." --add-data "output.mp3:." "web.py"