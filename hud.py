"""
hud.py - Interfaccia utente sovrapposta al tabellone
==================================================

Elementi UI:
  - PlayerNames: gestione nomi giocatori
  - TurnBanner: banner turno in cima
  - DiceDisplay: dado grande risultato
  - Leaderboard: classifica laterale sinistra
  - MessageBar: barra messaggi bottom
  - Toolbar: pulsanti top-right
  - SettingsPopup: overlay impostazioni
"""

import math
import json
import os
import pygame
from costanti import PLAYER_COLORS, NUM_PLAYERS, PEDINE_PER_PLAYER


# =============================================================================
# PALETTE UI
# =============================================================================

# Dizionario colori per UI: sfondi, testi, bottoni
_COLOR = {
    "bg_dark": (18, 18, 22, 220),
    "bg_mid": (30, 30, 38, 210),
    "bg_light": (45, 45, 58, 200),
    "border": (70, 70, 90, 180),
    "text_hi": (240, 240, 240),
    "text_lo": (155, 155, 170),
    "gold": (255, 210, 50),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red_btn": (200, 50, 50),
    "red_hi": (230, 80, 80),
    "green_btn": (60, 160, 80),
    "green_hi": (80, 200, 100),
    "gray_btn": (60, 60, 75),
    "gray_hi": (85, 85, 105),
}


# =============================================================================
# UTILITY DI DISEGNO
# =============================================================================

def color_adjust(color, d):
    """Sposta ogni componente RGB di delta (positivi = piu chiaro, negativi = piu scuro)."""
    return tuple(max(0, min(255, c + d)) for c in color[:3])


def color_blend(c1, c2, t):
    """Interpolazione lineare tra due colori RGB. t=0.0 -> c1, t=1.0 -> c2."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def gradient_vertical(surf, rect, r, ct, cb, at, ab):
    """Disegna un gradiente verticale dentro un rettangolo con angoli arrotondati."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    # Per ogni riga, calcola colore interpolato
    for row in range(h):
        t_row = row / max(h - 1, 1)
        c = color_blend(ct, cb, t_row)
        a = int(at + (ab - at) * t_row)
        # Calcola quanto tagliare per gli angoli arrotondati
        mg = max(0, r - min(row, h - 1 - row))
        pygame.draw.line(surf, (*c, a),
                        (x + mg, y + row), (x + w - 1 - mg, y + row))


def draw_panel(surf, rect, radius, c_top=(25, 25, 32), c_bot=(40, 40, 52),
               a_top=215, a_bot=200, border_color=None, border_w=1):
    """Disegna un pannello con gradiente, angoli arrotondati e bordo opzionale."""
    # Superficie temporanea con alpha per il gradiente
    tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    gradient_vertical(tmp, pygame.Rect(0, 0, rect.width, rect.height), 0,
                      c_top, c_bot, a_top, a_bot)
    # Maschera per angoli arrotondati (clip del gradiente)
    mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 0))
    pygame.draw.rect(mask, (255, 255, 255, 255),
                    pygame.Rect(0, 0, rect.width, rect.height),
                    border_radius=radius)
    tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(tmp, (rect.x, rect.y))
    # Bordo esterno opzionale
    if border_color:
        pygame.draw.rect(surf, (*border_color, 180),
                        rect, border_w, border_radius=radius)


def draw_player_dot(surf, cx, cy, r, color):
    """Disegna un pallino colorato con effetto riflesso."""
    # Cerchio principale colorato
    pygame.draw.circle(surf, color, (cx, cy), r)
    # Riflesso in alto a sinistra (piu chiaro)
    pygame.draw.circle(surf, color_adjust(color, +70), (cx - r // 3, cy - r // 3), max(r // 3, 1))
    # Bordo nero sottile
    pygame.draw.circle(surf, (0, 0, 0), (cx, cy), r, 1)


# =============================================================================
# PLAYER NAMES - Gestione nomi giocatori
# =============================================================================

class PlayerNames:
    """Gestisce i nomi dei giocatori. Legge da players.json o usa nomi generici."""
    
    def __init__(self, num_players):
        self._names = self._load(num_players)

    # -------------------------------------------------------------------------
    # Caricamento nomi da file
    # -------------------------------------------------------------------------
    def _load(self, n):
        # Prova a leggere da players.json nella stessa cartella
        path = os.path.join(os.path.dirname(__file__), "players.json")
        if os.path.exists(path):
            try:
                data = json.load(open(path, encoding="utf-8"))
                return [str(data[i]) if i < len(data) else f"Giocatore {i+1}"
                        for i in range(n)]
            except Exception:
                pass
        # Fallback: nomi generici
        return [f"Giocatore {i+1}" for i in range(n)]

    def get(self, index):
        """Restituisce il nome del giocatore index."""
        if 0 <= index < len(self._names):
            return self._names[index]
        return f"Giocatore {index+1}"

    def set_names(self, names_list):
        """Aggiorna i nomi (chiamato dalla schermata di login)."""
        self._names = list(names_list)


# =============================================================================
# TURN BANNER - Banner turno in cima a sinistra
# =============================================================================

# Mappatura fasi di gioco -> messaggi mostrati all'utente
_PHASE_LABELS = {
    "WAITING FOR ROLL": "In attesa del lancio del dado...",
    "DICE ANIMATION": "Lancio del dado...",
    "WAITING FOR MOVE": "Scegli una pedina!",
    "PIECE ANIMATION": "Pedina in movimento...",
    "MESSAGE DISPLAY": "...",
    "GAME OVER": "Partita terminata!",
}


def phase_label(phase_name: str) -> str:
    """Converte il nome della fase nel messaggio da mostrare."""
    return _PHASE_LABELS.get(phase_name, "")


class TurnBanner:
    """Banner che mostra il turno corrente con animazione slide-in."""
    
    def __init__(self):
        self._font_lbl = None
        self._font_name = None
        self._font_hint = None
        self._last_player = -1
        self._anim_t = 0.0
        self._ANIM_DUR = 0.35

    def _ensure_fonts(self):
        if self._font_lbl is None:
            self._font_lbl = pygame.font.SysFont("Consolas", 13, bold=False)
            self._font_name = pygame.font.SysFont("Consolas", 20, bold=True)
            self._font_hint = pygame.font.SysFont("Consolas", 12)

    def notify_new_turn(self, player_index):
        """Avvia l'animazione quando cambia il giocatore."""
        if player_index != self._last_player:
            self._last_player = player_index
            self._anim_t = 0.0

    def update(self, dt):
        """Aggiorna il timer dell'animazione."""
        if self._anim_t < 1.0:
            self._anim_t = min(1.0, self._anim_t + dt / self._ANIM_DUR)

    def draw(self, screen, current_player, phase_name, player_name, sw):
        self._ensure_fonts()

        # Colore del giocatore corrente per la striscia
        color = PLAYER_COLORS[current_player]
        
        # Dimensioni banner
        w, h = 260, 64
        target_x = 14
        target_y = 14
        
        # Animazione slide da sinistra (entra da fuori schermo)
        t_ease = 1 - (1 - self._anim_t) ** 3
        off_x = int(-w * (1 - t_ease))
        x = target_x + off_x
        y = target_y
        r = 14

        # Creazione superficie con alpha
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Pannello principale con gradiente scuro
        draw_panel(surf, pygame.Rect(0, 0, w, h), r,
                   c_top=(22, 22, 28), c_bot=(38, 38, 50),
                   a_top=220, a_bot=205,
                   border_color=(60, 60, 80), border_w=1)

        # Striscia colore giocatore (sinistra del banner)
        stripe_w = 5
        stripe = pygame.Surface((stripe_w, h - 24), pygame.SRCALPHA)
        for row in range(h - 24):
            t_row = row / max(h - 25, 1)
            # Gradiente dalla tinta giocatore verso scuro
            c = color_blend(color, color_adjust(color, -40), t_row)
            pygame.draw.line(stripe, (*c, 230), (0, row), (stripe_w - 1, row))
        surf.blit(stripe, (1, 12))

        # Label "TURNO" + pallino colore
        lbl = self._font_lbl.render("TURNO", True, _COLOR["text_lo"])
        surf.blit(lbl, (14, 7))

        dot_x = 14 + lbl.get_width() + 10
        draw_player_dot(surf, dot_x, 7 + lbl.get_height() // 2, 7, color)

        # Nome giocatore grande
        name_surf = self._font_name.render(player_name, True, _COLOR["text_hi"])
        surf.blit(name_surf, (14, 22))

        # Messaggio fase di gioco (sotto, con colore giocatore)
        phase_str = phase_label(phase_name)
        hint = self._font_hint.render(phase_str, True, (*color[:3], 200))
        surf.blit(hint, (14, h - hint.get_height() - 6))

        # Effetto vetro in cima (highlight)
        glass = pygame.Surface((w, h // 2), pygame.SRCALPHA)
        gradient_vertical(glass, pygame.Rect(1, 1, w - 2, h // 2 - 1), r,
                          (255, 255, 255), (255, 255, 255), 20, 2)
        surf.blit(glass, (0, 0))

        # Render sullo schermo
        screen.blit(surf, (x, y))
        return pygame.Rect(x, y, w, h)


# =============================================================================
# DICE DISPLAY - Mostra risultato dado grande in alto a destra
# =============================================================================

class DiceDisplay:
    """Mostra il valore del dado con animazione bounce/scale."""
    
    def __init__(self):
        self._font_big = None
        self._font_lbl = None
        self._anim_t = 1.0
        self._last_roll = 0

    def _ensure_fonts(self):
        if self._font_big is None:
            self._font_big = pygame.font.SysFont("Consolas", 36, bold=True)
            self._font_lbl = pygame.font.SysFont("Consolas", 12)

    def notify_roll(self, value):
        """Avvia l'animazione quando viene lanciato il dado."""
        self._last_roll = value
        self._anim_t = 0.0

    def notify_hide(self):
        """Nasconde il pannello (reset stato)."""
        self._last_roll = 0
        self._anim_t = 1.0

    def update(self, dt):
        if self._anim_t < 1.0:
            self._anim_t = min(1.0, self._anim_t + dt / 0.4)

    def draw(self, screen, dice_roll, sw):
        self._ensure_fonts()
        if self._last_roll <= 0:
            return
        dice_roll = self._last_roll

        # Posizione: sopra la toolbar, angolo destro
        TOOLBAR_BOTTOM = 68
        w, h = 78, 78
        x = sw - w - 14
        y = TOOLBAR_BOTTOM

        # Animazione scale (bounce iniziale)
        t_ease = 1 - (1 - self._anim_t) ** 2
        scale = 0.6 + 0.4 * t_ease
        rw, rh = int(w * scale), int(h * scale)
        rx = x + (w - rw) // 2
        ry = y + (h - rh) // 2

        # Creazione superficie ridimensionata
        surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
        r = 12

        # Pannello chiaro (diverso dal solito scuro)
        draw_panel(surf, pygame.Rect(0, 0, rw, rh), r,
                   c_top=(245, 245, 245), c_bot=(210, 210, 210),
                   a_top=250, a_bot=250,
                   border_color=(80, 80, 80), border_w=2)

        # Numero del dado (rosso per 6)
        font_size = max(8, int(36 * scale))
        font_scaled = pygame.font.SysFont("Consolas", font_size, bold=True)
        num_s = font_scaled.render(str(dice_roll), True,
                                  (200, 30, 30) if dice_roll == 6 else (20, 20, 20))
        # Piccolo offset verticale per effetto ottico
        v_offset = int(num_s.get_height() * 0.10)
        surf.blit(num_s, (rw // 2 - num_s.get_width() // 2,
                          rh // 2 - num_s.get_height() // 2 + v_offset))

        # Effetto vetro in cima
        glass = pygame.Surface((rw, rh // 2), pygame.SRCALPHA)
        gradient_vertical(glass, pygame.Rect(1, 1, rw - 2, rh // 2 - 2), r,
                         (255, 255, 255), (255, 255, 255), 55, 5)
        surf.blit(glass, (0, 0))

        screen.blit(surf, (rx, ry))


# =============================================================================
# LEADERBOARD - Classifica laterale a sinistra
# =============================================================================

class Leaderboard:
    """Classifica giocatori ordinata per pedine al traguardo."""
    
    def __init__(self):
        self._font_title = None
        self._font_hdr = None
        self._font_row = None

    def _ensure_fonts(self):
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("Consolas", 16, bold=True)
            self._font_row = pygame.font.SysFont("Consolas", 15, bold=False)
            # Prova font con emoji (caduta su Windows)
            for name in ("Segoe UI Emoji", "Segoe UI", "Arial Unicode MS", "Consolas"):
                f = pygame.font.SysFont(name, 12)
                if f:
                    self._font_hdr = f
                    break

    def draw(self, screen, players, player_names, current_player, sh):
        self._ensure_fonts()

        # Ordina giocatori per ranking (pedine al traguardo + avanzamento)
        ranked = sorted(players, key=lambda p: p.ranking_score(), reverse=True)

        # Layout: dimensioni e posizioni colonne
        row_h = 34
        pad = 12
        w = 248
        COL_POS = 8
        COL_DOT = 30
        COL_NAME = 60
        COL_FINAL = 196
        COL_HOME = 222
        DOT_R = 9

        # Calcolo altezza totale e posizione (centrato verticalmente)
        title_h = 32
        hdr_h = 22
        h = title_h + hdr_h + len(ranked) * row_h + pad
        x = 14
        y = max(sh // 2 - h // 2, 90)
        r = 14

        # Pannello principale scuro
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        draw_panel(surf, pygame.Rect(0, 0, w, h), r,
                   c_top=(20, 20, 28), c_bot=(35, 35, 48),
                   a_top=225, a_bot=215,
                   border_color=(60, 60, 85), border_w=1)

        # Barra oro in cima
        k = 20
        pygame.draw.rect(surf, (*_COLOR["gold"], 220),
                        pygame.Rect((k / 2), 0, (w - k), 4), border_radius=r)

        # Titolo "CLASSIFICA"
        title = self._font_title.render("CLASSIFICA", True, _COLOR["gold"])
        surf.blit(title, (pad, 10))

        # Separatore sotto il titolo
        sep_y = title_h - 4
        pygame.draw.line(surf, (*_COLOR["border"][:3], 140),
                        (pad, sep_y), (w - pad, sep_y), 1)

        # Header colonne
        hdr_y = title_h + 2
        for txt, hx in [("#", COL_POS), ("GIOCATORE", COL_NAME),
                         ("🏆", COL_FINAL), ("🏠", COL_HOME)]:
            s = self._font_hdr.render(txt, True, _COLOR["text_lo"])
            surf.blit(s, (hx, hdr_y))

        # Separatore sotto header
        pygame.draw.line(surf, (*_COLOR["border"][:3], 90),
                        (pad, hdr_y + 16), (w - pad, hdr_y + 16), 1)

        # Righe giocatori
        for i, player in enumerate(ranked):
            ry = title_h + hdr_h + i * row_h
            pid = player.index
            is_current = (pid == current_player)

            # Evidenziazione riga giocatore corrente (sfondo colorato)
            if is_current:
                hi = pygame.Surface((w - 2, row_h), pygame.SRCALPHA)
                hi_c = PLAYER_COLORS[pid]
                gradient_vertical(hi, pygame.Rect(0, 0, w - 2, row_h), 0,
                                  hi_c, hi_c, 35, 18)
                surf.blit(hi, (1, ry))
                # Barra colorata a sinistra
                pygame.draw.rect(surf, (*PLAYER_COLORS[pid], 220),
                                pygame.Rect(1, ry + 2, 3, row_h - 4))

            # Posizione (oro/argento/bronzo per i primi 3)
            pos_c = (_COLOR["gold"] if i == 0 else
                     (190, 190, 190) if i == 1 else
                     (180, 120, 60) if i == 2 else _COLOR["text_lo"])
            ps = self._font_row.render(f"{i+1}", True, pos_c)
            surf.blit(ps, (COL_POS, ry + (row_h - ps.get_height()) // 2))

            # Pallino colore giocatore
            dot_r = DOT_R + 2 if is_current else DOT_R
            draw_player_dot(surf, COL_DOT + dot_r, ry + row_h // 2, dot_r, PLAYER_COLORS[pid])

            # Nome giocatore + emoji AI per bot
            name = player_names.get(pid)
            max_chars = 11
            if len(name) > max_chars:
                name = name[:max_chars - 1] + "."
            name_c = _COLOR["white"] if is_current else _COLOR["text_hi"]

            AI_EMOJI = {
                'Scimmia': '(🐒)', 'Lepre': '(🐇)', 'Tartaruga': '(🐢)',
                'Leone': '(🦁)', 'Stratega': '(🧠)',
            }
            if getattr(player, 'is_bot', False):
                # Bot: nome + emoji livello AI
                ai_level = getattr(player, 'ai_level', '')
                emoji = AI_EMOJI.get(ai_level, '🤖')
                emoji_surf = self._font_hdr.render(emoji, True, name_c)
                name_surf = self._font_row.render(name, True, name_c)
                surf.blit(name_surf, (COL_NAME, ry + (row_h - name_surf.get_height()) // 2))
                surf.blit(emoji_surf, (COL_NAME + name_surf.get_width() + 4,
                                      ry + (row_h - emoji_surf.get_height()) // 2))
            else:
                # Giocatore umano: solo nome
                ns = self._font_row.render(name, True, name_c)
                surf.blit(ns, (COL_NAME, ry + (row_h - ns.get_height()) // 2))

            # Pedine al traguardo (🏆)
            fc = player.count_pedine_in_final()
            fc_c = _COLOR["gold"] if fc > 0 else _COLOR["text_lo"]
            fs = self._font_row.render(str(fc), True, fc_c)
            surf.blit(fs, (COL_FINAL, ry + (row_h - fs.get_height()) // 2))

            # Pedine in casa (🏠)
            hc = player.count_pedine_in_home()
            hc_s = self._font_row.render(str(hc), True,
                                          (100, 130, 200) if hc > 0 else _COLOR["text_lo"])
            surf.blit(hc_s, (COL_HOME, ry + (row_h - hc_s.get_height()) // 2))

            # Separatore tra righe
            if i < len(ranked) - 1:
                pygame.draw.line(surf, (*_COLOR["border"][:3], 55),
                                 (pad, ry + row_h - 1), (w - pad, ry + row_h - 1), 1)

        # Effetto vetro in cima alla classifica
        glass_h = h // 4
        glass = pygame.Surface((w, glass_h), pygame.SRCALPHA)
        gradient_vertical(glass, pygame.Rect(0, 0, w, glass_h), 0,
                         (255, 255, 255), (255, 255, 255), 14, 0)
        mask = pygame.Surface((w, glass_h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         pygame.Rect(0, 0, w, glass_h), border_radius=r)
        glass.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(glass, (0, 0))

        screen.blit(surf, (x, y))


# =============================================================================
# MESSAGE BAR - Barra messaggi in basso
# =============================================================================

class MessageBar:
    """Barra messaggi in basso con animazione slide-up e fade-out."""
    
    _SLIDE_DUR = 0.10
    _SHOW_DUR = 1.6
    _FADE_DUR = 0.12

    def __init__(self):
        self._font = None
        self._queue = []
        self._current = None
        self._state = "idle"
        self._t = 0.0
        self._enabled = True

    def _ensure_fonts(self):
        if self._font is None:
            for name in ("Segoe UI Emoji", "Segoe UI", "Arial Unicode MS", "Consolas"):
                self._font = pygame.font.SysFont(name, 16, bold=True)
                if self._font:
                    break

    def set_enabled(self, value: bool):
        """Abilita o disabilita la visualizzazione dei messaggi."""
        self._enabled = value
        if not value:
            self._queue = []
            self._current = None
            self._state = "idle"
            self._t = 0.0

    def push(self, text):
        if self._enabled:
            self._queue.append(text)

    def update(self, dt):
        # Stato idle: aspetta messaggi in coda
        if self._state == "idle":
            if self._queue:
                self._current = self._queue.pop(0)
                self._state = "slide_in"
                self._t = 0.0
            return
        
        # Se c'è un altro messaggio in coda e ne è passato abbastanza, vai a fade
        if self._state == "show" and self._queue and self._t > 0.5:
            self._state = "fade_out"
            self._t = 0.0
            return

        self._t += dt

        # Transizioni di stato basate sul timer
        if self._state == "slide_in":
            if self._t >= self._SLIDE_DUR:
                self._state = "show"
                self._t = 0.0

        elif self._state == "show":
            if self._t >= self._SHOW_DUR:
                self._state = "fade_out"
                self._t = 0.0

        elif self._state == "fade_out":
            if self._t >= self._FADE_DUR:
                self._state = "idle"
                self._current = None
                self._t = 0.0

    def draw(self, screen, sw, sh):
        self._ensure_fonts()
        if self._state == "idle" or self._current is None:
            return

        # Dimensioni e posizione
        w = min(sw - 80, 620)
        h = 44
        cx = sw // 2
        base_y = sh - h - 16
        r = 10

        # Calcolo offset e alpha in base allo stato
        if self._state == "slide_in":
            # Entra dal basso con fade in
            t_ease = 1 - (1 - self._t / self._SLIDE_DUR) ** 3
            off_y = int(h * 1.5 * (1 - t_ease))
            alpha = int(255 * t_ease)
        elif self._state == "show":
            # Completamente visibile
            off_y, alpha = 0, 255
        else:  # fade_out
            # Esce con fade out
            t_ease = self._t / self._FADE_DUR
            off_y = 0
            alpha = int(255 * (1 - t_ease))

        y = base_y + off_y
        
        # Pannello scuro
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        draw_panel(surf, pygame.Rect(0, 0, w, h), r,
                   c_top=(22, 22, 30), c_bot=(35, 35, 48),
                   a_top=220, a_bot=210,
                   border_color=(80, 80, 110), border_w=1)
        
        # Testo centrato
        txt = self._font.render(self._current, True, (235, 235, 235))
        surf.blit(txt, (w // 2 - txt.get_width() // 2,
                        h // 2 - txt.get_height() // 2))

        # Applica alpha e render
        surf.set_alpha(alpha)
        screen.blit(surf, (cx - w // 2, y))


# =============================================================================
# TOOLBAR - Pulsanti in alto a destra
# =============================================================================

ACTION_SETTINGS = "settings"
ACTION_RESET = "reset"
ACTION_QUIT = "quit"


class _Button:
    """Classe interna per rappresentare un bottone della toolbar."""
    def __init__(self, icon, color_normal, color_hover, action, tooltip=""):
        self.icon = icon
        self.cn = color_normal
        self.ch = color_hover
        self.action = action
        self.tip = tooltip
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.hovered = False


class Toolbar:
    """Toolbar in alto a destra con 3 bottoni: Impostazioni, Reset, Esci."""
    
    _BTN_SIZE = 34
    _GAP = 6

    def __init__(self):
        self._font_icon = None
        self._font_tip = None
        self._buttons = [
            _Button("⚙", _COLOR["gray_btn"], _COLOR["gray_hi"], ACTION_SETTINGS, "Impostazioni"),
            _Button("↺", _COLOR["gray_btn"], _COLOR["gray_hi"], ACTION_RESET, "Reset partita"),
            _Button("✕", _COLOR["red_btn"], _COLOR["red_hi"], ACTION_QUIT, "Esci"),
        ]

    def _ensure_fonts(self):
        if self._font_icon is None:
            self._font_icon = pygame.font.SysFont("Segoe UI Emoji", 18)
            self._font_tip = pygame.font.SysFont("Consolas", 11)

    def handle_event(self, event):
        # Click sinistro: restituisce l'azione del bottone premuto
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._buttons:
                if btn.rect.collidepoint(event.pos):
                    return btn.action
        # Movimento mouse: aggiorna stato hover
        if event.type == pygame.MOUSEMOTION:
            for btn in self._buttons:
                btn.hovered = btn.rect.collidepoint(event.pos)
        return None

    def draw(self, screen, sw):
        self._ensure_fonts()

        bs = self._BTN_SIZE
        gap = self._GAP
        n = len(self._buttons)
        
        # Calcolo posizione (angolo alto a destra)
        total_w = n * bs + (n - 1) * gap
        start_x = sw - total_w - 14
        y = 14

        # Pannello di sfondo toolbar
        panel_w = total_w + gap * 2
        panel_h = bs + gap * 2
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        draw_panel(panel, pygame.Rect(0, 0, panel_w, panel_h), 10,
                   border_color=(60, 60, 80), border_w=1)
        screen.blit(panel, (start_x - gap, y - gap))

        # Disegno bottoni
        for i, btn in enumerate(self._buttons):
            bx = start_x + i * (bs + gap)
            btn.rect = pygame.Rect(bx, y, bs, bs)

            # Colore base o hover
            c = btn.ch if btn.hovered else btn.cn
            
            # Superficie bottone con gradiente
            btn_surf = pygame.Surface((bs, bs), pygame.SRCALPHA)
            draw_panel(btn_surf, pygame.Rect(0, 0, bs, bs), 8,
                       c_top=color_adjust(c, +15), c_bot=color_adjust(c, -15),
                       a_top=240, a_bot=240,
                       border_color=(0, 0, 0), border_w=1)

            # Effetto vetro in cima
            glass = pygame.Surface((bs, bs // 2), pygame.SRCALPHA)
            gradient_vertical(glass, pygame.Rect(0, 0, bs, bs // 2), 8,
                              (255, 255, 255), (255, 255, 255), 30, 2)
            btn_surf.blit(glass, (0, 0))

            # Icona emoji centrata
            icon = self._font_icon.render(btn.icon, True, (230, 230, 230))
            btn_surf.blit(icon, (bs // 2 - icon.get_width() // 2,
                                  bs // 2 - icon.get_height() // 2))
            screen.blit(btn_surf, (bx, y))

            # Tooltip quando in hover
            if btn.hovered and btn.tip:
                tip = self._font_tip.render(btn.tip, True, (220, 220, 220))
                tw, th = tip.get_width() + 10, tip.get_height() + 6
                tx = bx + bs // 2 - tw // 2
                ty = y + bs + 4
                ts = pygame.Surface((tw, th), pygame.SRCALPHA)
                ts.fill((20, 20, 28, 210))
                pygame.draw.rect(ts, (80, 80, 100, 180),
                                pygame.Rect(0, 0, tw, th), 1, border_radius=4)
                ts.blit(tip, (5, 3))
                screen.blit(ts, (tx, ty))


# =============================================================================
# SETTINGS POPUP - Overlay impostazioni
# =============================================================================

ACTION_GOTO_MENU = "goto_menu"
ACTION_RESET_GAME = "reset_game"
ACTION_TOGGLE_MUTE = "toggle_mute"
ACTION_TOGGLE_MUTE_SFX = "toggle_mute_sfx"
ACTION_TOGGLE_MUTE_MUSIC = "toggle_mute_music"
ACTION_TOGGLE_MESSAGES = "toggle_messages"
ACTION_CLOSE_POPUP = "close_popup"
ACTION_END_GAME = "end_game"
ACTION_TOGGLE_FULLSCREEN = "toggle_fullscreen"


class _PopupButton:
    """Classe interna per rappresentare un bottone nel popup impostazioni."""
    def __init__(self, label, action, color=(50, 50, 65), hover=(70, 70, 90)):
        self.label = label
        self.action = action
        self.color = color
        self.hover = hover
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.hovered = False


class SettingsPopup:
    """Overlay modale per le impostazioni in-game con animazione scale."""
    
    _ANIM_DUR = 0.20

    def __init__(self):
        self._open = False
        self._anim_t = 0.0
        self._muted = False
        self._muted_sfx = False
        self._muted_music = False
        self._fullscreen = False
        self._msg_enabled = True
        self._font_t = None
        self._font_b = None
        self._font_s = None
        self._buttons = []
        self._rebuild_buttons()

    def _rebuild_buttons(self, fullscreen=False):
        # Labels che cambiano in base allo stato (mute on/off)
        mute_label = "🔇 Tutto: OFF" if self._muted else "🔊 Tutto: ON"
        sfx_label = "🔕 SFX: OFF" if self._muted_sfx else "🔔 SFX: ON"
        music_label = "⏹ Musica: OFF" if self._muted_music else "▶ Musica: ON"
        msg_label = "💬 Messaggi: OFF" if not self._msg_enabled else "💬 Messaggi: ON"
        
        self._fullscreen = fullscreen
        self._buttons = [
            _PopupButton("🏠  Torna al menu", ACTION_GOTO_MENU, (35, 55, 80), (50, 80, 115)),
            _PopupButton("⏹  Termina partita", ACTION_END_GAME, (100, 40, 40), (140, 55, 55)),
            _PopupButton("↺  Reset partita", ACTION_RESET_GAME, (80, 45, 35), (115, 65, 50)),
            _PopupButton(mute_label, ACTION_TOGGLE_MUTE, (40, 60, 45), (55, 85, 60)),
            _PopupButton(sfx_label, ACTION_TOGGLE_MUTE_SFX, (35, 55, 45), (50, 78, 58)),
            _PopupButton(music_label, ACTION_TOGGLE_MUTE_MUSIC, (35, 45, 60), (50, 65, 85)),
            _PopupButton(msg_label, ACTION_TOGGLE_MESSAGES, (40, 50, 70), (55, 70, 100)),
            _PopupButton("✕  Chiudi", ACTION_CLOSE_POPUP, (45, 45, 55), (65, 65, 80)),
        ]

    def _ensure_fonts(self):
        if self._font_t is None:
            self._font_t = pygame.font.SysFont("Consolas", 20, bold=True)
            self._font_b = pygame.font.SysFont("Segoe UI Emoji", 15, bold=True)
            self._font_s = pygame.font.SysFont("Consolas", 11)

    @property
    def is_open(self):
        return self._open

    @property
    def muted(self):
        return self._muted

    @property
    def muted_sfx(self):
        return self._muted_sfx

    @property
    def muted_music(self):
        return self._muted_music

    @property
    def msg_enabled(self):
        return self._msg_enabled

    def open(self):
        self._open = True
        self._anim_t = 0.0

    def close(self):
        self._open = False

    def update(self, dt):
        if self._open and self._anim_t < 1.0:
            self._anim_t = min(1.0, self._anim_t + dt / self._ANIM_DUR)

    def handle_event(self, event):
        if not self._open:
            return None
        
        # Click sinistro su bottone
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._buttons:
                if btn.rect.collidepoint(event.pos):
                    # Toggle stati per bottoni toggle
                    if btn.action == ACTION_TOGGLE_MUTE:
                        self._muted = not self._muted
                        self._rebuild_buttons(self._fullscreen)
                    elif btn.action == ACTION_TOGGLE_MUTE_SFX:
                        self._muted_sfx = not self._muted_sfx
                        self._rebuild_buttons(self._fullscreen)
                    elif btn.action == ACTION_TOGGLE_MUTE_MUSIC:
                        self._muted_music = not self._muted_music
                        self._rebuild_buttons(self._fullscreen)
                    elif btn.action == ACTION_TOGGLE_MESSAGES:
                        self._msg_enabled = not self._msg_enabled
                        self._rebuild_buttons(self._fullscreen)
                    elif btn.action == ACTION_CLOSE_POPUP:
                        self.close()
                    return btn.action
            # Click fuori dai bottoni: chiudi
            self.close()
            return ACTION_CLOSE_POPUP
        
        # Hover mouse: aggiorna stato bottoni
        if event.type == pygame.MOUSEMOTION:
            for btn in self._buttons:
                btn.hovered = btn.rect.collidepoint(event.pos)
        
        # Tasto ESC: chiudi
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return ACTION_CLOSE_POPUP
        
        return None

    def draw(self, screen, sw, sh):
        if not self._open:
            return
        self._ensure_fonts()

        # Animazione scale + alpha
        t_ease = 1 - (1 - self._anim_t) ** 3
        scale = 0.75 + 0.25 * t_ease
        alpha = int(255 * t_ease)

        # Dimensioni base popup
        pw, ph = 300, 430
        px = sw // 2 - pw // 2
        py = sh // 2 - ph // 2

        # Sfondo scuro semi-trasparente (scrim)
        scrim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        scrim.fill((0, 0, 0, int(140 * t_ease)))
        screen.blit(scrim, (0, 0))

        # Calcola dimensioni ridimensionate per animazione
        rw = int(pw * scale)
        rh = int(ph * scale)
        rx = sw // 2 - rw // 2
        ry = sh // 2 - rh // 2

        # Popup principale
        popup = pygame.Surface((pw, ph), pygame.SRCALPHA)
        r = 18

        draw_panel(popup, pygame.Rect(0, 0, pw, ph), r,
                   c_top=(22, 22, 30), c_bot=(38, 38, 52),
                   a_top=250, a_bot=245,
                   border_color=(75, 75, 100), border_w=2)

        # Effetto vetro in cima
        glass_h = min(ph // 3, 60)
        glass = pygame.Surface((pw, glass_h), pygame.SRCALPHA)
        gradient_vertical(glass, pygame.Rect(0, 0, pw, glass_h), 0,
                          (255, 255, 255), (255, 255, 255), 18, 0)
        mask = pygame.Surface((pw, glass_h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         pygame.Rect(0, 0, pw, glass_h), border_radius=r)
        glass.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        popup.blit(glass, (0, 0))

        # Titolo "IMPOSTAZIONI"
        title = self._font_t.render("IMPOSTAZIONI", True, _COLOR["text_hi"])
        popup.blit(title, (pw // 2 - title.get_width() // 2, 14))
        pygame.draw.line(popup, (*_COLOR["border"][:3], 140),
                        (16, 40), (pw - 16, 40), 1)

        # Layout bottoni
        # I bottoni SFX e MUSICA sono messi affiancati (paired layout)
        PAIRED = {ACTION_TOGGLE_MUTE_SFX, ACTION_TOGGLE_MUTE_MUSIC}
        bh = 40
        b_gap = 10
        b_w = pw - 48
        b_start_y = 58
        bx_base = 24

        row_y = b_start_y
        skip_next = False

        # Loop bottoni
        for i, btn in enumerate(self._buttons):
            if skip_next:
                skip_next = False
                continue

            next_btn = self._buttons[i + 1] if i + 1 < len(self._buttons) else None
            is_pair = (btn.action in PAIRED and next_btn is not None
                       and next_btn.action in PAIRED)

            if is_pair:
                # Bottoni affiancati (SFX | MUSICA)
                half_w = (b_w - b_gap) // 2
                for col, b in enumerate([btn, next_btn]):
                    bx_col = bx_base + col * (half_w + b_gap)
                    b.rect = pygame.Rect(px + bx_col, py + row_y, half_w, bh)
                    c = b.hover if b.hovered else b.color
                    bs = pygame.Surface((half_w, bh), pygame.SRCALPHA)
                    draw_panel(bs, pygame.Rect(0, 0, half_w, bh), 10,
                               c_top=color_adjust(c, +12), c_bot=color_adjust(c, -8),
                               a_top=240, a_bot=235,
                               border_color=(60, 60, 80), border_w=1)
                    gh = pygame.Surface((half_w, bh // 2), pygame.SRCALPHA)
                    gradient_vertical(gh, pygame.Rect(0, 0, half_w, bh // 2), 10,
                                      (255, 255, 255), (255, 255, 255), 28, 2)
                    bs.blit(gh, (0, 0))
                    lbl = self._font_b.render(b.label, True, (225, 225, 225))
                    bs.blit(lbl, (half_w // 2 - lbl.get_width() // 2,
                                  bh // 2 - lbl.get_height() // 2))
                    popup.blit(bs, (bx_col, row_y))
                skip_next = True
            else:
                # Bottone normale (larghezza piena)
                btn.rect = pygame.Rect(px + bx_base, py + row_y, b_w, bh)
                c = btn.hover if btn.hovered else btn.color
                bs = pygame.Surface((b_w, bh), pygame.SRCALPHA)
                draw_panel(bs, pygame.Rect(0, 0, b_w, bh), 10,
                           c_top=color_adjust(c, +12), c_bot=color_adjust(c, -8),
                           a_top=240, a_bot=235,
                           border_color=(60, 60, 80), border_w=1)
                gh = pygame.Surface((b_w, bh // 2), pygame.SRCALPHA)
                gradient_vertical(gh, pygame.Rect(0, 0, b_w, bh // 2), 10,
                                 (255, 255, 255), (255, 255, 255), 28, 2)
                bs.blit(gh, (0, 0))
                lbl = self._font_b.render(btn.label, True, (225, 225, 225))
                bs.blit(lbl, (b_w // 2 - lbl.get_width() // 2,
                              bh // 2 - lbl.get_height() // 2))
                popup.blit(bs, (bx_base, row_y))

            row_y += bh + b_gap

        # Render finale con ridimensionamento per animazione
        scaled = pygame.transform.smoothscale(popup, (rw, rh))
        scaled.set_alpha(alpha)
        screen.blit(scaled, (rx, ry))
