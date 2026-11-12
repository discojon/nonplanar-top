@echo off
setlocal EnableExtensions
title nonplanar_top installer
echo.
echo  nonplanar_top - installer for Windows
echo  -------------------------------------
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo  Python was not found.
  echo  Install Python 3.10 or newer from https://www.python.org/downloads/
  echo  and tick "Add python.exe to PATH" in the installer, then run this again.
  echo.
  pause
  exit /b 1
)

echo  Installing the Python libraries (numpy, scipy, shapely, opencv-python)...
py -3 -m pip install --upgrade --user numpy scipy shapely opencv-python
if errorlevel 1 (
  echo.
  echo  pip could not install the libraries. Check your internet connection and try again.
  pause
  exit /b 1
)

set "DEST=C:\PrusaTools\nonplanar"
if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%~dp0nonplanar_top.py" "%DEST%\" >nul
if exist "%DEST%\nonplanar_top.ini" (
  echo  Keeping your existing settings file: %DEST%\nonplanar_top.ini
) else (
  copy "%~dp0nonplanar_top.ini" "%DEST%\" >nul
)

for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)"') do set "PYEXE=%%P"
set "LINE="%PYEXE%" "%DEST%\nonplanar_top.py""

echo.
echo  Installed to %DEST%
echo.
echo  Next steps:
echo   1. Measure your fan shroud height and put it in %DEST%\nonplanar_top.ini
echo   2. In PrusaSlicer (Expert mode): Print Settings ^> Output options ^> Post-processing scripts
echo      paste this line (it is also on your clipboard now):
echo.
echo      %LINE%
echo.
echo   3. In Print Settings ^> Notes type the word:  nonplanar
echo      and save the print profile under a new name.
echo.
echo %LINE%| clip
pause
