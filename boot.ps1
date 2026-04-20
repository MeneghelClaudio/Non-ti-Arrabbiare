# Evita problemi con policy temporaneamente
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

Write-Host "=== Avvio gioco ==="

# Verifica Python
$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python non trovato. Installa Python e riprova."
    pause
    exit
}

# Crea venv se non esiste
if (!(Test-Path "venv")) {
    Write-Host "Creo ambiente virtuale..."
    py -m venv venv
}

# Attiva venv
Write-Host "Attivo ambiente virtuale..."
& .\venv\Scripts\Activate.ps1

# Aggiorna pip (silenzioso)
Write-Host "Aggiorno pip..."
python -m pip install --upgrade pip > $null

# Installa pygame-ce (ultima versione)
Write-Host "Installo pygame-ce..."
pip install pygame-ce

if ($LASTEXITCODE -ne 0) {
    Write-Host "Errore durante installazione di pygame-ce"
    pause
    exit
}

# Avvio gioco
Write-Host "Avvio gioco..."
python main.py

pause