@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Proxy IPv6 Manager - chay 1 lenh tren Windows/Linux
echo ============================================================
echo.
echo LUU Y: Neu muon tu set IPv6 va tao proxy, hay bam chuot phai file nay
echo       va chon "Run as administrator".
echo.

where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"

if not defined PY (
    echo [LOI] Khong tim thay Python.
    echo Vui long cai Python 3.9+ va tick "Add python.exe to PATH".
    pause
    exit /b 1
)

echo File nay se goi run_proxyv6.py de tu tao venv, cai pip/thu vien,
echo tu nhan Windows/Linux, tu chon card mang, tao mac dinh 3 proxy va mo UI.
echo.
%PY% run_proxyv6.py %*

pause
