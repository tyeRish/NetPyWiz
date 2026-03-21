@echo off
title NetPyWiz Installer
color 0D

echo.
echo  ######################################
echo  ##  NETPYWIZ // WINDOWS INSTALLER  ##
echo  ######################################
echo.

:: Check for admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo  ERROR: Please run as Administrator
    echo  Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo  [1/3] Checking Npcap...
reg query "HKLM\SOFTWARE\Npcap" >nul 2>&1
if %errorLevel% neq 0 (
    echo  Npcap not found. Downloading installer...
    curl -L "https://npcap.com/dist/npcap-1.79.exe" -o "%TEMP%\npcap_installer.exe"
    echo  Installing Npcap...
    "%TEMP%\npcap_installer.exe" /S
    if %errorLevel% neq 0 (
        echo  ERROR: Npcap installation failed
        echo  Please install manually from https://npcap.com
        pause
        exit /b 1
    )
    echo  Npcap installed successfully
) else (
    echo  Npcap: OK
)

echo  [2/3] Installing NetPyWiz...
if not exist "%ProgramFiles%\NetPyWiz" mkdir "%ProgramFiles%\NetPyWiz"
copy /Y "NetPyWiz.exe" "%ProgramFiles%\NetPyWiz\NetPyWiz.exe"

:: Create Desktop shortcut
echo  [3/3] Creating shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\NetPyWiz.lnk'); $s.TargetPath = '%ProgramFiles%\NetPyWiz\NetPyWiz.exe'; $s.Description = 'NetPyWiz Network Monitor'; $s.Save()"

echo.
echo  ######################################
echo  ##  INSTALLATION COMPLETE          ##
echo  ######################################
echo.
echo  Run NetPyWiz from your Desktop shortcut
echo  NOTE: Always run as Administrator for full functionality
echo.
pause
