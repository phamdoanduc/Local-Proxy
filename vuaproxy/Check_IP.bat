@echo off
title VuaProxy - Quick IP Checker
color 0a
echo.
echo ==============================================
echo        VUAPROXY - QUICK IP CHECKER
echo ==============================================
echo.
set /p port="[-] Nhap cong (Port) can kiem tra (Mac dinh: 5555): "
if "%port%"=="" set port=5555

echo.
echo [*] Dang kiem tra ket noi qua 127.0.0.1:%port%...
echo.

:: Use curl (built-in Windows 10/11) to fetch exit IP
curl -s -x 127.0.0.1:%port% --connect-timeout 5 http://api.ipify.org > ip_result.txt

if %errorlevel% neq 0 (
    color 0c
    echo [!] LOI: Khong the ket noi qua Proxy tai cong %port%!
    echo [!] Vui long kiem tra xem VuaProxy_Local.exe da chay chua.
) else (
    set /p exit_ip=<ip_result.txt
    echo [OK] Ket noi THANH CONG!
    echo [>] IP Thoat cua ban la: %exit_ip%
    del ip_result.txt
)

echo.
echo ==============================================
pause
