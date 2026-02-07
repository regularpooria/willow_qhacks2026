#!/bin/bash
# Simple setup script for Linux/Mac
pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
export PLAYWRIGHT_BROWSERS_PATH=0
playwright install chromium
pyinstaller --noconfirm --onefile --windowed --name "Willow" --icon "favicon.ico" --add-data "web:web"  "web.py"