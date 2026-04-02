"""
draw.py - Rendering del tabellone di gioco
=========================================

Responsabilità:
  - Sfondo con gradiente e pattern
  - Bracci e centro del tabellone
  - Celle del percorso
  - Case dei giocatori
  - Animazioni (transizioni, ripple)
  - Pedine e indicatori
  - Dado

Principi di design:
  • ZERO noise/sgranatura: solo gradienti e forme vettoriali pulite
  • Sfondo con sfumatura radiale morbida
  • Bracci con pannello colorato satinato + bordo sottile
  • Celle 3D con highlight/shadow a mezzaluna (smooth)
  • Celle start con stella dorata a 5 punte
  • Celle final con gradiente colore player + bordo dorato
  • Home: gradiente verticale pulito + riflesso vetro
  • Centro: alone morbido + sunburst + gradiente concentrico
  • Connessioni colorate per final path
  • HUD panel con gradiente verticale liscio
"""

import math
import pygame
from costanti import *

# Fallback costanti opzionali
DEBUG_SHOW_NUMBERS = False
ARM_COLOR_ALPHA = 50
HOME_CORNER_RATIO = 0.18


# =============================================================================
# UTILITY
# =============================================================================

def polar(angle_deg, length):
    """Converte angolo in gradi e lunghezza in coordinate cartesiane."""
    rad = math.radians(angle_deg - 90)
    return math.cos(rad) * length, math.sin(rad) * length


def player_angle(player, num_players):
    """Restituisce l'angolo in gradi per un giocatore."""
    return (360 / num_players) * player


def adjust_color(color, delta):
    """Sposta ogni componente RGB di delta (range 0-255)."""
    return tuple(max(0, min(255, c + delta)) for c in color)


def blend_color(c1, c2, t):
    """Interpolazione lineare tra due colori RGB."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_circle(screen, pos, radius, fill, border=BLACK, border_width=2):
    """Disegna un cerchio con bordo opzionale."""
    pygame.draw.circle(screen, fill, (int(pos[0]), int(pos[1])), max(int(radius), 1))
    if border_width > 0:
        pygame.draw.circle(screen, border, (int(pos[0]), int(pos[1])), max(int(radius), 1), border_width)


def draw_triangle(screen, points, color, border=BLACK, border_width=2):
    """Disegna un triangolo con bordo opzionale."""
    pygame.draw.polygon(screen, color, points)
    if border_width > 0:
        pygame.draw.polygon(screen, border, points, border_width)


def hsv_to_rgb(h, s, v):
    """Converte HSV a RGB."""
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return r + m, g + m, b + m


# =============================================================================
# SFONDO - gradiente radiale morbido, animato per giocatore corrente
# =============================================================================

# Abilita/disabilita effetti singoli
BG_ENABLE_RIPPLE = True
BG_ENABLE_PATTERN = True

# Parametri effetto ripple
BG_RIPPLE_SPEED = 80
BG_RIPPLE_INTERVAL = 1
BG_RIPPLE_ALPHA = 150
BG_RIPPLE_WIDTH = 50

# Parametri pattern esagonale
BG_PATTERN_SIZE = 72
BG_PATTERN_ALPHA = 255
BG_PATTERN_SPEED = 0

# Stato interno per animazioni
_bg_state = {
    "from_color": None,
    "to_color": None,
    "current_color": None,
    "t": 1.0,
    "last_player": -1,
}

_ripple_state = {
    "rings": [],
    "spawn_timer": 0.0,
    "pattern_phase": 0.0,
}

BG_TRANSITION_SPEED = 2.8

# Cache per il board statico
_board_cache = {
    "surface": None,
    "last_player": -1,
    "last_size": None,
    "bg_color": None,
    "dirty": True,
}


def invalidate_board_cache():
    """Forza il ridisegno del board al prossimo frame."""
    _board_cache["dirty"] = True


def make_bg_base(player_color):
    """Calcola il colore base dello sfondo dalla tinta del giocatore."""
    r, g, b = player_color
    return (
        max(0, min(255, int(r * 0.55 + 255 * 0.45))),
        max(0, min(255, int(g * 0.55 + 255 * 0.45))),
        max(0, min(255, int(b * 0.55 + 255 * 0.45))),
    )


def notify_player_change(new_player):
    """Avvia la transizione colore quando cambia il giocatore."""
    state = _bg_state
    if state["last_player"] == new_player:
        return
    new_color = make_bg_base(PLAYER_COLORS[new_player])
    if state["current_color"] is None:
        state["current_color"] = new_color
        state["from_color"] = new_color
    else:
        state["from_color"] = state["current_color"]
    state["to_color"] = new_color
    state["t"] = 0.0
    state["last_player"] = new_player


def update_background(dt, center_radius):
    """Aggiorna le animazioni dello sfondo ogni frame."""
    state = _bg_state
    if state["t"] < 1.0:
        state["t"] = min(1.0, state["t"] + dt * BG_TRANSITION_SPEED)
        t = state["t"]
        ease = t * t * (3 - 2 * t)  # Smoothstep
        fc = state["from_color"]
        tc = state["to_color"]
        state["current_color"] = tuple(
            int(fc[i] + (tc[i] - fc[i]) * ease) for i in range(3)
        )

    rs = _ripple_state

    if BG_ENABLE_RIPPLE:
        rs["spawn_timer"] += dt
        if rs["spawn_timer"] >= BG_RIPPLE_INTERVAL:
            rs["spawn_timer"] = 0.0
            rs["rings"].append({"r": 0.0, "max_r": center_radius})
        for ring in rs["rings"]:
            ring["r"] += BG_RIPPLE_SPEED * dt
        rs["rings"] = [rg for rg in rs["rings"] if rg["r"] < rg["max_r"]]


_hex_cache = {"surface": None, "color": None, "size_key": None}


def draw_hex_pattern(surf, base_color, phase):
    """
    Pattern di esagoni. Cachato e ricalcolato solo se cambia colore o dimensione.
    La pulsazione viene applicata all'alpha senza ridisegnare.
    """
    w, h = surf.get_size()
    size_key = (w, h)
    color = adjust_color(base_color, +DARKER)

    if (_hex_cache["surface"] is None
            or _hex_cache["color"] != color
            or _hex_cache["size_key"] != size_key):
        size = BG_PATTERN_SIZE
        pat = pygame.Surface((w, h), pygame.SRCALPHA)
        col_w = size * 1.5
        row_h = size * math.sqrt(3)
        cols = int(w / col_w) + 3
        rows = int(h / row_h) + 3
        for col in range(-1, cols):
            for row in range(-1, rows):
                x = col * col_w
                y = row * row_h + (col % 2) * (row_h / 2)
                pts = []
                for k in range(6):
                    angle = math.radians(60 * k)
                    pts.append((x + size * math.cos(angle),
                                y + size * math.sin(angle)))
                pygame.draw.polygon(pat, (*color, BG_PATTERN_ALPHA), pts, 1)
        _hex_cache["surface"] = pat
        _hex_cache["color"] = color
        _hex_cache["size_key"] = size_key

    # Applica alpha pulsante
    pulse = math.sin(phase) * 0.4 + 0.6
    pat_copy = _hex_cache["surface"].copy()
    pat_copy.set_alpha(int(255 * pulse))
    surf.blit(pat_copy, (0, 0))


def draw_background(canvas, center_x, center_y, current_player):
    """Disegna lo sfondo completo con gradiente, pattern e vignetta."""
    w, h = canvas.get_size()
    notify_player_change(current_player)

    base = _bg_state["current_color"] or make_bg_base(PLAYER_COLORS[current_player])
    idx = _bg_state["last_player"] if _bg_state["last_player"] >= 0 else current_player
    pure = PLAYER_COLORS[idx]
    cx, cy = int(center_x), int(center_y)
    max_r = int(math.hypot(w, h) * 0.72)

    canvas.fill("#FFFFFF")

    if BG_ENABLE_PATTERN:
        draw_hex_pattern(canvas, base, 0.0)

    # Gradiente radiale: centro saturo puro → bordi pastello
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 18
    for i in range(steps, 0, -1):
        t_r = i / steps
        ease_t = t_r ** 1.6
        r_px = int(max_r * t_r)
        blend = tuple(int(pure[j] * ease_t + base[j] * (1 - ease_t)) for j in range(3))
        alpha = int(175 * ease_t)
        pygame.draw.circle(grad, (*blend, alpha), (cx, cy), r_px)
    canvas.blit(grad, (0, 0))

    # Vignetta scura ai bordi
    vign = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = adjust_color(base, -55)
    for i in range(12, 0, -1):
        r_px = int(max_r * i / 12)
        alpha = int(50 * ((1 - i / 12) ** 2.2))
        pygame.draw.circle(vign, (*dark, alpha), (cx, cy), r_px)
    canvas.blit(vign, (0, 0))


# =============================================================================
# BRACCI - pannello satinato con tinta colore
# =============================================================================

def draw_arm_backgrounds(canvas, cell_size, arm_length, center_x, center_y, center_radius):
    """Disegna i bracci del tabellone."""
    arm_surf = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
    ARM_GRAY = (235, 235, 235, 255)

    home_size = cell_size * 3
    width_ratio = 1.5
    rect_w = int(home_size * width_ratio)
    home_dist = arm_length * 1.20
    home_outer = home_dist + home_size / 2
    overhang = (rect_w - home_size) / 2
    arm_len = home_outer + overhang

    r_ends = int(home_size * HOME_CORNER_RATIO)
    pad = 2

    surf_w = rect_w + pad * 2
    surf_h = int(arm_len) + r_ends + pad * 2

    for p in range(NUM_PLAYERS):
        angle = player_angle(p, NUM_PLAYERS)

        pygame.draw.circle(canvas, (0, 0, 0), (int(center_x), int(center_y)),
                          int(center_radius + cell_size * 2) + 2)

        local = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        pygame.draw.rect(local, ARM_GRAY,
                        pygame.Rect(pad, pad, rect_w, int(arm_len) + r_ends),
                        border_radius=r_ends)

        pygame.draw.rect(local, (0, 0, 0, 255),
                        pygame.Rect(pad, pad, rect_w, int(arm_len) + r_ends),
                        width=2, border_radius=r_ends)

        rotated = pygame.transform.rotate(local, -angle)

        mid_dist = arm_len / 2 - r_ends / 2
        mid_dx, mid_dy = polar(angle, mid_dist)
        mid_x = center_x + mid_dx
        mid_y = center_y + mid_dy
        rx = int(mid_x - rotated.get_width() / 2)
        ry = int(mid_y - rotated.get_height() / 2)
        arm_surf.blit(rotated, (rx, ry))

    canvas.blit(arm_surf, (0, 0))


# =============================================================================
# CELLE - bevel 3D con highlight/shadow
# =============================================================================

def draw_cell_bevel(canvas, cx, cy, r, fill_color, border_color=(140, 140, 140), border_w=1):
    """
    Cella circolare con effetto 3D:
    - Cerchio pieno
    - Highlight ellittico in alto
    - Bordo netto
    """
    cx, cy, r = int(cx), int(cy), max(int(r), 2)

    pygame.draw.circle(canvas, fill_color, (cx, cy), r)

    # Highlight ellittico in alto
    hl_w = max(int(r * 1.0), 2)
    hl_h = max(int(r * 0.42), 1)
    hl_x = cx - hl_w // 2
    hl_y = cy - r + max(int(r * 0.12), 1)
    hl_surf = pygame.Surface((hl_w, hl_h), pygame.SRCALPHA)
    pygame.draw.ellipse(hl_surf, (255, 255, 255, 75),
                        pygame.Rect(0, 0, hl_w, hl_h))
    canvas.blit(hl_surf, (hl_x, hl_y))

    if border_w > 0:
        pygame.draw.circle(canvas, border_color, (cx, cy), r, border_w)


def draw_star5(canvas, cx, cy, r):
    """Stella dorata a 5 punte."""
    outer = r * 0.78
    inner = r * 0.33
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        ro = outer if i % 2 == 0 else inner
        pts.append((cx + math.cos(angle) * ro, cy + math.sin(angle) * ro))
    pygame.draw.polygon(canvas, (255, 215, 0), pts)
    pygame.draw.polygon(canvas, (180, 110, 0), pts, 1)
    pygame.draw.circle(canvas, (255, 245, 150), (int(cx), int(cy)), max(int(r * 0.15), 1))


def draw_cells(canvas, path_cells, final_paths, cell_radius):
    """Disegna tutte le celle del tabellone."""
    font = pygame.font.SysFont(None, max(int(cell_radius * 1.2), 8)) if DEBUG_SHOW_NUMBERS else None
    start_idx = 0

    for i, cell in enumerate(path_cells):
        if cell.is_start:
            color = PLAYER_COLORS[start_idx]
            light = adjust_color(color, +55)
            draw_cell_bevel(canvas, cell.x, cell.y, cell_radius,
                             light, adjust_color(color, -50), 2)
            draw_star5(canvas, int(cell.x), int(cell.y), cell_radius)
            start_idx += 1
        else:
            draw_cell_bevel(canvas, cell.x, cell.y, cell_radius,
                             (252, 252, 252), (160, 160, 160), 1)
        if DEBUG_SHOW_NUMBERS and font:
            t = font.render(str(i), True, (60, 60, 60))
            canvas.blit(t, t.get_rect(center=(cell.x, cell.y)))

    # Celle final: colore pieno del player
    for p, path in final_paths.items():
        color = PLAYER_COLORS[p]
        border = adjust_color(color, -50)
        for j, cell in enumerate(path):
            draw_cell_bevel(canvas, cell.x, cell.y, cell_radius,
                             color, border, 2)
            if DEBUG_SHOW_NUMBERS and font:
                tx = font.render(str(j), True, (60, 60, 60))
                canvas.blit(tx, tx.get_rect(center=(cell.x, cell.y)))


# =============================================================================
# HOME - quadrato con gradiente e riflesso vetro
# =============================================================================

def make_home_surface(isize, color):
    """
    Superficie per la casa del giocatore:
    - Ombra esterna
    - Gradiente verticale
    - Riflesso vetro
    - Bordo esterno
    """
    pad = 6
    total = isize + pad * 2
    s = pygame.Surface((total, total), pygame.SRCALPHA)
    r = int(isize * HOME_CORNER_RATIO)
    ox = pad

    # Gradiente verticale
    body = pygame.Surface((isize, isize), pygame.SRCALPHA)
    light = adjust_color(color, +PASTEL)
    dark = adjust_color(color, +DARKER)
    for row in range(isize):
        t = row / max(isize - 1, 1)
        c = blend_color(light, dark, t)
        pygame.draw.line(body, c, (0, row), (isize - 1, row))

    # Clip angoli arrotondati
    clip = pygame.Surface((isize, isize), pygame.SRCALPHA)
    pygame.draw.rect(clip, (255, 255, 255, 255),
                    pygame.Rect(0, 0, isize, isize), border_radius=r)
    body.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(body, (ox, ox))

    # Riflesso vetro
    glass = pygame.Surface((isize, isize), pygame.SRCALPHA)
    pygame.draw.ellipse(glass, (255, 255, 255, 58),
                        pygame.Rect(int(isize * 0.08), int(isize * 0.07),
                                    int(isize * 0.84), int(isize * 0.38)))
    glass.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(glass, (ox, ox))

    # Bordo
    pygame.draw.rect(s, (20, 20, 20, 220),
                     pygame.Rect(ox, ox, isize, isize), 2, border_radius=r)

    return s, pad


def draw_home(canvas, home_cells, get_home_geometry):
    """Disegna le case dei giocatori con i loro slot."""
    for p in range(NUM_PLAYERS):
        hx, hy, size = get_home_geometry(p)
        angle = player_angle(p, NUM_PLAYERS)
        isize = int(size)

        home_surf, pad = make_home_surface(isize, PLAYER_COLORS[p])
        rotated = pygame.transform.rotate(home_surf, -angle)
        rw, rh = rotated.get_size()
        canvas.blit(rotated, (int(hx - rw / 2), int(hy - rh / 2)))

        # Celle slot
        for cell in home_cells[p]:
            draw_cell_bevel(canvas, cell.x, cell.y, size * 0.16,
                             (255, 255, 255), (170, 170, 170), 1)


# =============================================================================
# CENTRO - alone morbido + gradiente concentrico
# =============================================================================

def draw_center(canvas, center_x, center_y, center_radius, cell_size, current_player):
    """Disegna il centro del tabellone."""
    color = adjust_color(PLAYER_COLORS[current_player], +DARKER)
    outer_r = int(center_radius + cell_size * 2)
    inner_r = int(center_radius)
    cx, cy = int(center_x), int(center_y)

    # Alone colorato morbido
    glow = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
    gc = color
    for i in range(8, 0, -1):
        rg = int(outer_r * 1.25 * i / 8)
        alpha = int(20 * ((1 - i / 8) ** 1.6))
        pygame.draw.circle(glow, (*gc, alpha), (cx, cy), rg)
    canvas.blit(glow, (0, 0))

    # Anello grigio base
    pygame.draw.circle(canvas, (235, 235, 235), (cx, cy), outer_r)

    # Gradiente concentrico
    csurf = pygame.Surface((inner_r * 2 + 4, inner_r * 2 + 4), pygame.SRCALPHA)
    steps = 12
    for i in range(steps, 0, -1):
        rr = int(inner_r * i / steps)
        t = 1 - (i / steps)
        c = blend_color(adjust_color(color, +70), adjust_color(color, -20), t)
        pygame.draw.circle(csurf, c, (inner_r + 2, inner_r + 2), rr)
    canvas.blit(csurf, (cx - inner_r - 2, cy - inner_r - 2))

    # Bordo cerchio
    pygame.draw.circle(canvas, "#000000", (cx, cy), inner_r, 2)

    # Riflesso vetro
    hi = pygame.Surface((inner_r * 2, inner_r * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(hi, (255, 255, 255, 38),
                        pygame.Rect(int(inner_r * 0.18), int(inner_r * 0.10),
                                    int(inner_r * 1.0), int(inner_r * 0.55)))
    canvas.blit(hi, (cx - inner_r, cy - inner_r))


# =============================================================================
# CONNESSIONI - linee e archi tra celle
# =============================================================================

SPESSORE = 3


def draw_connections(canvas, path_cells, final_paths, center_x, center_y):
    """Disegna le connessioni tra celle (linee e archi)."""

    def arc_between(a, b, color=(110, 110, 110)):
        """Disegna un arco tra due celle."""
        ax, ay = a.x - center_x, a.y - center_y
        bx, by = b.x - center_x, b.y - center_y
        r = (math.hypot(ax, ay) + math.hypot(bx, by)) / 2
        aa = math.atan2(ay, ax)
        ab = math.atan2(by, bx)
        if NUM_PLAYERS % 2 == 1:
            off = math.pi / NUM_PLAYERS
            aa += off
            ab += off
        if ab < aa:
            aa, ab = ab, aa
        if ab - aa > math.pi:
            aa, ab = ab, aa + 2 * math.pi
        rect = pygame.Rect(center_x - r, center_y - r, 2 * r, 2 * r)
        pygame.draw.arc(canvas, color, rect, aa, ab, SPESSORE - 1)

    # Percorso principale
    for i in range(len(path_cells)):
        a, b = path_cells[i], path_cells[(i + 1) % len(path_cells)]
        if getattr(a, 'is_intersection', False) or getattr(b, 'is_intersection', False):
            arc_between(a, b)
        else:
            pygame.draw.line(canvas, (115, 115, 115),
                             (int(a.x), int(a.y)), (int(b.x), int(b.y)), SPESSORE)

    # Final paths (linee colorate)
    for p, path in final_paths.items():
        lc = adjust_color(PLAYER_COLORS[p], -35)
        for a, b in zip(path, path[1:]):
            pygame.draw.line(canvas, lc,
                             (int(a.x), int(a.y)), (int(b.x), int(b.y)), SPESSORE)

    # Collegamento cella end → primo final
    for cell in path_cells:
        if getattr(cell, "is_end", False):
            arm = getattr(cell, "player", None)
            if arm is not None and arm in final_paths and final_paths[arm]:
                ff = final_paths[arm][0]
                lc = adjust_color(PLAYER_COLORS[arm], -20)
                pygame.draw.line(canvas, lc,
                                (int(cell.x), int(cell.y)),
                                (int(ff.x), int(ff.y)), SPESSORE)


# =============================================================================
# PEDINE
# =============================================================================

def draw_pawns(canvas, players, cell_size):
    """
    Disegna le pedine in ordine:
    1. Pedine non animate
    2. Pedine animate
    3. Indicatori (triangoli)
    """
    for player in players:
        for pawn in player:
            if not pawn.is_animating():
                pawn.draw(canvas, cell_size)
    for player in players:
        for pawn in player:
            if pawn.is_animating():
                pawn.draw(canvas, cell_size)
    for player in players:
        for pawn in player:
            pawn.draw_indicator(canvas, cell_size)


# =============================================================================
# HUD - pannello info (debug)
# =============================================================================

def gradient_rect(surf, rect, r, c_top, c_bot, a_top, a_bot):
    """Gradiente verticale liscio dentro rect."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    for row in range(h):
        t = row / max(h - 1, 1)
        col = (
            int(c_top[0] + (c_bot[0] - c_top[0]) * t),
            int(c_top[1] + (c_bot[1] - c_top[1]) * t),
            int(c_top[2] + (c_bot[2] - c_top[2]) * t),
            int(a_top + (a_bot - a_top) * t),
        )
        mg = max(0, r - min(row, h - 1 - row))
        pygame.draw.line(surf, col,
                         (x + mg, y + row), (x + w - 1 - mg, y + row))


def draw_info(screen, font, current_phase, current_player, dice_roll):
    """Pannello info (fase, giocatore, dado)."""
    phase_str = str(current_phase).split('.')[-1].replace('_', ' ')
    player_color = PLAYER_COLORS[current_player]

    font_lbl = pygame.font.SysFont("Consolas", 15)
    font_val = pygame.font.SysFont("Consolas", 17, bold=True)
    font_ttl = pygame.font.SysFont("Consolas", 13)

    rows = [
        ("FASE", phase_str),
        ("GIOCATORE", str(current_player + 1)),
        ("DADO", str(dice_roll) if dice_roll > 0 else "–"),
    ]

    padding = 14
    stripe_w = 5
    row_h = 28
    title_h = 22
    corner_r = 12

    max_lw = max(font_lbl.size(r[0])[0] for r in rows)
    max_vw = max(font_val.size(r[1])[0] for r in rows)
    panel_w = max(stripe_w + padding + max_lw + 16 + max_vw + padding, 255)
    panel_h = title_h + len(rows) * row_h + padding
    px, py = 14, 14

    ps = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    gradient_rect(ps, pygame.Rect(0, 0, panel_w, panel_h), corner_r,
                   (25, 25, 25), (50, 50, 50), 205, 185)

    border_s = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(border_s, (*player_color, 210),
                     pygame.Rect(0, 0, panel_w, panel_h), 2, border_radius=corner_r)
    ps.blit(border_s, (0, 0))

    glass = pygame.Surface((panel_w, panel_h // 2), pygame.SRCALPHA)
    gradient_rect(glass, pygame.Rect(1, 1, panel_w - 2, panel_h // 2 - 1),
                   corner_r, (255, 255, 255), (255, 255, 255), 26, 3)
    ps.blit(glass, (0, 0))

    pygame.draw.rect(ps, (*player_color, 248),
                     pygame.Rect(0, corner_r, stripe_w, panel_h - corner_r * 2))

    t_surf = font_ttl.render("LUDO BOARD", True, (155, 155, 155))
    ps.blit(t_surf, (stripe_w + padding, 5))

    sep_y = title_h + 1
    pygame.draw.line(ps, (*player_color, 110),
                    (stripe_w + padding, sep_y), (panel_w - padding, sep_y), 1)

    for i, (label, value) in enumerate(rows):
        ty = sep_y + 5 + i * row_h
        ls = font_lbl.render(label, True, (165, 165, 165))
        vs = font_val.render(value, True, (238, 238, 238))
        ps.blit(ls, (stripe_w + padding, ty + (row_h - ls.get_height()) // 2))
        ps.blit(vs, (panel_w - padding - vs.get_width(),
                     ty + (row_h - vs.get_height()) // 2))

    sh = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 55),
                     pygame.Rect(0, 0, panel_w, panel_h), border_radius=corner_r)
    screen.blit(sh, (px + 4, py + 4))
    screen.blit(ps, (px, py))


# =============================================================================
# DRAW BOARD - entry point principale
# =============================================================================

def draw_board(screen, center_x, center_y, center_radius, cell_size, arm_length,
               path_cells, final_paths, home_cells, players, get_home_geometry,
               cell_radius, current_player, dado,
               screen_shake_x=0, screen_shake_y=0, dt=0.016):
    """
    Funzione principale di rendering del tabellone.
    Gestisce caching per ottimizzazione.
    """

    w, h = screen.get_size()

    notify_player_change(current_player)
    update_background(dt, center_radius)

    cur_size = (w, h)
    cur_color = _bg_state["current_color"]

    # Decide se ridisegnare il board statico
    in_transition = _bg_state["t"] < 1.0
    needs_redraw = (
        _board_cache["dirty"]
        or _board_cache["last_size"] != cur_size
        or _board_cache["last_player"] != current_player
        or in_transition
        or _board_cache["bg_color"] != cur_color
    )

    if needs_redraw:
        board_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        draw_background(board_surf, center_x, center_y, current_player)
        draw_arm_backgrounds(board_surf, cell_size, arm_length, center_x, center_y, center_radius)
        draw_center(board_surf, center_x, center_y, center_radius, cell_size, current_player)
        draw_connections(board_surf, path_cells, final_paths, center_x, center_y)
        draw_home(board_surf, home_cells, get_home_geometry)
        draw_cells(board_surf, path_cells, final_paths, cell_radius)

        _board_cache["surface"] = board_surf
        _board_cache["last_player"] = current_player
        _board_cache["last_size"] = cur_size
        _board_cache["bg_color"] = cur_color
        _board_cache["dirty"] = False
    else:
        board_surf = _board_cache["surface"]

    # Layer dinamico: pedine + ripple + dado
    canvas = pygame.Surface((w, h), pygame.SRCALPHA)
    canvas.blit(board_surf, (0, 0))

    # Ripple
    if BG_ENABLE_RIPPLE and _ripple_state["rings"]:
        cx, cy = int(center_x), int(center_y)
        max_r = int(math.hypot(w, h) * 0.72)
        ripple_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pure = PLAYER_COLORS[_bg_state["last_player"] if _bg_state["last_player"] >= 0 else current_player]
        ring_color = adjust_color(pure, +30)
        for ring in _ripple_state["rings"]:
            progress = ring["r"] / ring["max_r"]
            alpha = int(BG_RIPPLE_ALPHA * (1 - progress) ** 1.8)
            if alpha > 0:
                pygame.draw.circle(ripple_surf, (*ring_color, alpha),
                                   (cx, cy), int(ring["r"]), BG_RIPPLE_WIDTH)
        canvas.blit(ripple_surf, (0, 0))

    draw_pawns(canvas, players, cell_size)

    if dado is not None:
        dado.draw(canvas)

    screen.blit(canvas, (screen_shake_x, screen_shake_y))
