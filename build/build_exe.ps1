# =============================================================================
#  build_exe.ps1 — Compila "Non ti Arrabbiare.exe" standalone
#
#  USO:
#    powershell -ExecutionPolicy Bypass -File ".\build\build_exe.ps1"
#
#  OUTPUT:
#    build\Non ti Arrabbiare.exe   (cartella build nella directory del progetto)
# =============================================================================

$ErrorActionPreference = "Stop"

# ── Percorsi ──────────────────────────────────────────────────────────────────

if ($PSScriptRoot) {
    $ScriptDir = $PSScriptRoot
} else {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
# La cartella build è dove si trova lo script, il progetto è nella cartella padre
$ProjectDir = Split-Path -Parent $ScriptDir
$AppName    = "Non ti Arrabbiare"
$EntryPoint = Join-Path $ScriptDir "main.py"
$AssetsDir  = Join-Path $ProjectDir "assets"
$IconPath   = Join-Path $ProjectDir "assets\icon.ico"

$BuildOutDir = $ScriptDir  # Output nella stessa cartella dello script
$VenvDir    = Join-Path $ScriptDir "_build_venv"
$BuildDir   = Join-Path $ScriptDir "_build_tmp"
$DistDir    = Join-Path $ScriptDir "_build_dist"
$SpecFile   = Join-Path $BuildDir "$AppName.spec"
$FinalExe   = Join-Path $BuildOutDir "$AppName.exe"

# ── Funzione di cleanup ───────────────────────────────────────────────────────

function Cleanup {
    Write-Host ""
    Write-Host "[Cleanup] Rimozione file temporanei..." -ForegroundColor Yellow
    # Non elimina il venv per riutilizzarlo alla prossima build
    foreach ($item in @($BuildDir, $DistDir, $SpecFile)) {
        if (Test-Path $item) {
            Remove-Item $item -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  Rimosso: $item" -ForegroundColor DarkGray
        }
    }
}

# ── Intestazione ──────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Build: $AppName" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 0: Controlla Python ──────────────────────────────────────────────────

Write-Host "[0/5] Ricerca Python..." -ForegroundColor Yellow

$PythonExe = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python 3") {
            $PythonExe = $candidate
            Write-Host "  Trovato: $candidate  ($ver)" -ForegroundColor Green
            break
        }
    } catch { }
}

if (-not $PythonExe) {
    Write-Host "[ERRORE] Python 3 non trovato nel PATH." -ForegroundColor Red
    exit 1
}

# Rileva la versione major.minor per scegliere il pacchetto pygame giusto
$verStr     = (& $PythonExe --version 2>&1) -replace "Python ", ""
$verParts   = $verStr.Split(".")
$pyMajor    = [int]$verParts[0]
$pyMinor    = [int]$verParts[1]
Write-Host "  Versione Python: $pyMajor.$pyMinor" -ForegroundColor DarkGray

# ── Step 1: Pulizia ───────────────────────────────────────────────────────────

Write-Host ""
Write-Host "[1/5] Pulizia residui precedenti..." -ForegroundColor Yellow
Cleanup

# Crea cartella build se non esiste
if (-not (Test-Path $BuildOutDir)) {
    New-Item -ItemType Directory -Path $BuildOutDir -Force | Out-Null
}

# Rimuovi exe precedente dalla cartella build
$OldExe = Join-Path $BuildOutDir "$AppName.exe"
if (Test-Path $OldExe) {
    Remove-Item $OldExe -Force
    Write-Host "  Rimosso exe precedente." -ForegroundColor DarkGray
}

# ── Step 2: Crea/Riutilizza venv ────────────────────────────────────────────────

Write-Host ""
Write-Host "[2/5] Creazione/Riutilizzo venv..." -ForegroundColor Yellow

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

# Se il venv esiste già, salta creazione e installazione
if (Test-Path $VenvPython) {
    Write-Host "  Venv esistente riutilizzato." -ForegroundColor Green
} else {
    & $PythonExe -m venv $VenvDir
    if (-not (Test-Path $VenvPython)) {
        Write-Host "[ERRORE] Creazione venv fallita." -ForegroundColor Red
        Cleanup; exit 1
    }
    Write-Host "  Venv creato." -ForegroundColor Green
}

# ── Step 3: Installa dipendenze (solo se venv nuovo) ──────────────────────────

Write-Host ""
Write-Host "[3/5] Installazione dipendenze..." -ForegroundColor Yellow
Write-Host ""

# Verifica se le dipendenze sono già installate
$depsInstalled = $false

Write-Host "  Verifica dipendenze..." -ForegroundColor DarkGray

# Check if packages exist in venv Lib directory
$pyinstallerPath = Join-Path $VenvDir "Lib\site-packages\pyinstaller"
$pygamePath = Join-Path $VenvDir "Lib\site-packages\pygame"

if ((Test-Path $pyinstallerPath) -and (Test-Path $pygamePath)) {
    Write-Host "  pyinstaller: trovato" -ForegroundColor DarkGray
    Write-Host "  pygame: trovato" -ForegroundColor DarkGray
    $depsInstalled = $true
} else {
    if (-not (Test-Path $pyinstallerPath)) {
        Write-Host "  pyinstaller: non trovato" -ForegroundColor DarkGray
    }
    if (-not (Test-Path $pygamePath)) {
        Write-Host "  pygame: non trovato" -ForegroundColor DarkGray
    }
}

if ($depsInstalled) {
    Write-Host "  Dipendenze presenti, skip dell'installazione." -ForegroundColor Green
} else {
    # Installa pyinstaller (skip pip upgrade per velocizzare)
    Write-Host "  Installazione pyinstaller..." -ForegroundColor DarkGray
    & $VenvPython -m pip install --quiet --no-cache-dir pyinstaller 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRORE] Installazione pyinstaller fallita." -ForegroundColor Red
        Cleanup; exit 1
    }

    # Sceglie il pacchetto pygame in base alla versione Python
    if ($pyMajor -eq 3 -and $pyMinor -ge 13) {
        $pygamePkg = "pygame-ce"
    } else {
        $pygamePkg = "pygame"
    }
    Write-Host "  Installazione $pygamePkg..." -ForegroundColor DarkGray
    & $VenvPython -m pip install --quiet --no-cache-dir $pygamePkg 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRORE] Installazione $pygamePkg fallita." -ForegroundColor Red
        Cleanup; exit 1
    }
    Write-Host "  Dipendenze installate." -ForegroundColor Green
}

# ── Step 4: Build con PyInstaller ────────────────────────────────────────────

Write-Host ""
Write-Host "[4/5] Build PyInstaller --onefile..." -ForegroundColor Yellow
Write-Host ""

$PyArgs = @(
    "--onefile",
    "--noconsole",
    "--name=$AppName",
    "--distpath=$DistDir",
    "--workpath=$BuildDir",
    "--specpath=$BuildDir",
    "--log-level=WARN"
)

# Assets (suoni, musica, eventuali immagini)
if (Test-Path $AssetsDir) {
    $PyArgs += "--add-data"
    $PyArgs += "${AssetsDir};assets"
    Write-Host "  Assets inclusi: $AssetsDir" -ForegroundColor DarkGray
} else {
    Write-Host "  [AVVISO] Cartella assets non trovata." -ForegroundColor Yellow
}

# Icona opzionale
if (Test-Path $IconPath) {
    $PyArgs += "--icon=$IconPath"
}

$PyArgs += $EntryPoint

# Esegui pyinstaller tramite il Python del venv (evita problemi di PATH)
& $VenvPython -m PyInstaller @PyArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRORE] PyInstaller ha restituito un errore." -ForegroundColor Red
    Cleanup; exit 1
}

# ── Step 5: Sposta il .exe e pulisce ─────────────────────────────────────────

Write-Host ""
Write-Host "[5/5] Finalizzazione..." -ForegroundColor Yellow

$BuiltExe = Join-Path $DistDir "$AppName.exe"

if (-not (Test-Path $BuiltExe)) {
    Write-Host "[ERRORE] Il file .exe non e' stato creato." -ForegroundColor Red
    Cleanup; exit 1
}

# Copia l'exe nella cartella build
Copy-Item $BuiltExe $FinalExe -Force
Write-Host "  Spostato: $FinalExe" -ForegroundColor Green

# Copia anche i file Python necessari nella cartella build (solo se non già presenti)
if (-not (Test-Path (Join-Path $BuildOutDir "main.py"))) {
    Copy-Item (Join-Path $ProjectDir "main.py") $BuildOutDir -Force
    Write-Host "  Copiato main.py" -ForegroundColor Green
}
if (-not (Test-Path (Join-Path $BuildOutDir "base_path.py"))) {
    Copy-Item (Join-Path $ProjectDir "base_path.py") $BuildOutDir -Force
    Write-Host "  Copiato base_path.py" -ForegroundColor Green
}

# Cleanup di tutti i file temporanei (venv, build, dist, spec)
Cleanup

# ── Risultato ─────────────────────────────────────────────────────────────────

$SizeMB = [math]::Round((Get-Item $FinalExe).Length / 1MB, 1)

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Build completata con successo!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  File:       $FinalExe" -ForegroundColor White
Write-Host "  Dimensione: $SizeMB MB" -ForegroundColor White
Write-Host ""
Write-Host "  Standalone: Python, pygame, moduli e assets inclusi." -ForegroundColor Gray
Write-Host "  Puoi spostarlo ovunque senza dipendenze esterne." -ForegroundColor Gray
Write-Host ""

Start-Process explorer.exe -ArgumentList "/select,`"$FinalExe`""