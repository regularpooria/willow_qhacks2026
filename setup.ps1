# Simple setup script for Windows
pip install virtualenv
virtualenv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PLAYWRIGHT_BROWSERS_PATH="0"
playwright install chromium
pyinstaller --noconfirm --onefile --windowed --name "Willow" --icon "favicon.ico" --add-data "web:web"  "web.py"