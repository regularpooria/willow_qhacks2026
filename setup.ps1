# Simple setup script for Windows
pip install virtualenv
virtualenv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PLAYWRIGHT_BROWSERS_PATH="0"
playwright install chromium
pyinstaller --noconfirm --onefile --windowed --icon "favicon.ico" --name "Willow" --add-data "records:records/" --add-data "public:public/" --add-data "web:web/" --add-data ".env:."  "web.py"
