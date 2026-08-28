# Sobe backend + frontend + tunel ngrok para testar o app no celular.
# Uso:  powershell -ExecutionPolicy Bypass -File tunnel-teste.ps1
# Encerra tudo com Ctrl+C nesta janela (ou feche as janelas abertas).

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$ngrok = "D:\controle_acesso\ngrok.exe"

Write-Host "-> Backend Django em http://127.0.0.1:8000" -ForegroundColor Cyan
Start-Process -FilePath "$root\backend\venv\Scripts\python.exe" `
  -ArgumentList "manage.py","runserver","127.0.0.1:8000" `
  -WorkingDirectory "$root\backend"

Write-Host "-> Frontend Vite (porta 5173/5174)" -ForegroundColor Cyan
Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" -WorkingDirectory "$root\frontend"

Start-Sleep -Seconds 6

# Descobre em qual porta o Vite subiu
$vitePort = 5173
foreach ($p in 5173,5174,5175) {
  try { Invoke-WebRequest "http://127.0.0.1:$p/" -UseBasicParsing -TimeoutSec 2 | Out-Null; $vitePort = $p; break } catch {}
}
Write-Host "-> Vite na porta $vitePort" -ForegroundColor Green

Write-Host "-> Tunel ngrok -> porta $vitePort" -ForegroundColor Cyan
& $ngrok http $vitePort
