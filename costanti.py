"""
costanti.py - Costanti globali del gioco Non t'Arrabbiare
==========================================================

Questo file viene importato da tutti i moduli.
NOTA: I valori possono essere sovrascritti da ludo.py al runtime
in base al file game_config.json.
"""

# =============================================================================
# CONFIGURAZIONE GIOCO
# =============================================================================

NUM_PLAYERS = 9                    # Numero massimo di giocatori
FINAL_CELLS = 4                    # Celle nel percorso finale (traguardo)
CELLS_PER_ARM = FINAL_CELLS + 1    # Celle per braccio del tabellone (5)
PEDINE_PER_PLAYER = 4              # Pedine per ogni giocatore

# =============================================================================
# ANIMAZIONI E MOVIMENTO
# =============================================================================

PEDINE_SPEED = 4.0                 # Velocità animazione pedine (pixel/frame)
PEDINE_JUMP_HEIGHT = 1.0           # Altezza del salto 3D durante movimento
ANIMATION_DELAY = 0.05             # Pausa tra un passo e l'altro (secondi)

# =============================================================================
# EFFETTI VISIVI
# =============================================================================

SCREEN_SHAKE_AMPLITUDE = 2.0       # Ampiezza shake schermo in pixel
SCREEN_SHAKE_TIME = 5.0            # Durata shake schermo (secondi)
SCREEN_SHAKE_DECAY = 10.0          # Velocità di decadimento shake

# =============================================================================
# COLORI GIOCATORI (RGB)
# =============================================================================

PLAYER_COLORS = [
    (255,   0,   0),    # 0: rosso
    (255, 149,   0),    # 1: arancione
    (255, 255,   0),    # 2: giallo
    (  0, 255,   0),    # 3: verde
    (  0, 247, 255),    # 4: azzurro
    ( 64,  64, 255),    # 5: blu
    (162,   0, 255),    # 6: viola
    (255,   0, 204),    # 7: fucsia
    (138,  84,  19),    # 8: marrone
    ( 97,  97,  97),    # 9: grigio
]

# =============================================================================
# MODIFICATORI COLORE
# =============================================================================

PASTEL = 120                       # Incremento RGB per toni pastello
DARKER = -70                       # Decremento RGB per toni scuri

# =============================================================================
# COLORI UI
# =============================================================================

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_GRAY = (240, 240, 240)
GOLD = (255, 215, 0)
SHADOW = (80, 80, 80)

# =============================================================================
# LAYOUT HOME
# =============================================================================

# Offset relativi per posizionare le 4 celle slot all'interno della casa
# (usati per calcolare le posizioni dei 4 slot rispetto al centro casa)
HOME_OFFSETS = [(-0.3, -0.3), (0.3, -0.3), (-0.3, 0.3), (0.3, 0.3)]
