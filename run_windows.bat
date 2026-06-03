@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Proxy IPv6 Manager - chay nhanh tren Windows
echo ============================================================
echo.
echo LUU Y: Neu muon tao/xoa IPv6, hay bam chuot phai file nay va chon
echo       "Run as administrator".
echo.

where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"

if not defined PY (
    echo [LOI] Khong tim thay Python.
    echo Vui long cai Python 3.9+ tu https://www.python.org/downloads/
    echo Khi cai nho tick "Add python.exe to PATH".
    pause
    exit /b 1
)

echo [1/4] Kiem tra Python...
%PY% --version
if errorlevel 1 (
    echo [LOI] Python khong chay duoc.
    pause
    exit /b 1
)

echo.
echo [2/4] Tao moi truong ao venv neu chua co...
if not exist "venv\Scripts\python.exe" (
    %PY% -m venv venv
    if errorlevel 1 (
        echo [LOI] Tao venv that bai.
        pause
        exit /b 1
    )
)

echo.
echo [3/4] Cai pip va thu vien can thiet...
call "venv\Scripts\activate.bat"
python -m ensurepip --upgrade
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [LOI] Cai thu vien that bai. Hay kiem tra Internet hoac requirements.txt.
    pause
    exit /b 1
)

echo.
echo [4/4] Khoi dong web server...
if "%PROXYV6_HOST%"=="" set "PROXYV6_HOST=0.0.0.0"
if "%PROXYV6_PORT%"=="" set "PROXYV6_PORT=9002"

echo.
echo Web UI local: http://127.0.0.1:%PROXYV6_PORT%
echo Web UI LAN  : http://IP-MAY-NAY:%PROXYV6_PORT%
echo.
echo Nhan Ctrl+C de dung server.
echo.

if "%NO_BROWSER%"=="" start "" "http://127.0.0.1:%PROXYV6_PORT%"
python server.py

pause
