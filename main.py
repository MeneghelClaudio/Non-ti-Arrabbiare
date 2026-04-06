"""
main.py - Punto di avvio del gioco Non t'Arrabbiare
Esegui questo file per iniziare a giocare.
"""

import subprocess
import os
import sys

# Avvia start_screen.py
script_dir = os.path.dirname(os.path.abspath(__file__))
start_path = os.path.join(script_dir, "start_screen.py")

if os.path.isfile(start_path):
    subprocess.Popen([sys.executable, start_path])
else:
    print(f"Errore: non trovo start_screen.py in {script_dir}")
