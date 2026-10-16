$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --noconsole --onedir --name NovaCommandCCTV --icon assets/favicon.ico --version-file file_version_info.txt --add-data "assets;assets" --collect-all customtkinter --collect-all selenium --collect-all pyautogui --collect-all pyperclip --hidden-import win32com.client --hidden-import pythoncom app.py
if ($LASTEXITCODE -ne 0) { throw "Error al compilar PyInstaller" }
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { throw "Instala Inno Setup 6 antes de continuar" }
& $iscc installer\NovaCommandCCTV.iss
if ($LASTEXITCODE -ne 0) { throw "Error al compilar instalador" }
Write-Host "Instalador creado en installer_output\NovaCommand_CCTV_Setup_v1.0.0.exe"
