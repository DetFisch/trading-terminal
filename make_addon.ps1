# Copies the app's code into the add-on folder so Home Assistant can build it.
# Run from the project folder before every push:  powershell -File make_addon.ps1
# Never copies .env, .venv, .cache or alerts.json: keys go into the add-on's Configuration tab.
$root = $PSScriptRoot
$dest = Join-Path $root "trading_terminal\app"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Path $dest | Out-Null
Copy-Item (Join-Path $root "app.py"), (Join-Path $root "requirements.txt") $dest
Copy-Item (Join-Path $root "terminal") $dest -Recurse
Copy-Item (Join-Path $root ".streamlit") $dest -Recurse
Get-ChildItem $dest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Write-Host "Add-on code refreshed in trading_terminal\app. Commit and push, then press Update in Home Assistant."
