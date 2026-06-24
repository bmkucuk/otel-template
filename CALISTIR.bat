@echo off
echo.
echo  ==========================================
echo   Otel Leo ^& Cunda Villa — Web (SQLite)
echo  ==========================================
echo.
python --version >nul 2>&1
if errorlevel 1 (echo HATA: Python bulunamadi! & pause & exit /b)
echo Bagimliliklar yukleniyor...
pip install -r requirements.txt --quiet
echo.
echo Sunucu baslatiliyor...
start "" "http://localhost:5000"
python app.py
pause
