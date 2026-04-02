"""
ludo.py - Game Loop principale
============================

Struttura import:
  1. Librerie standard
  2. Leggi game_config.json
  3. Patch costanti (PRIMA di importare draw/hud)
  4. Importa draw, hud, celle, ecc.
"""

import sys
import os
import json
import math
import random
from enum import Enum, auto
import pygame


# =============================================================================
# CONFIG - Leggi game_config.json
# =============================================================================

def _hex_to_rgb(h):
    """Converte hex a RGB tuple."""
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _load_config():
    """Carica la configurazione da file o args."""
    candidates = []
    if len(sys.argv) > 1:
        candidates.append(sys.argv[1])
    candidates.append(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_config.json")
    )
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ludo] Errore config {path}: {e}")
    return {}


_config = _load_config()


# =============================================================================
# PATCH COSTANTI (prima di importare draw/hud)
# =============================================================================

import costanti

if _config.get("players"):
    players_cfg = _config["players"]
    total = len(players_cfg)
    pawns = _config.get("pawns_each", 4)

    costanti.NUM_PLAYERS = total
    costanti.PEDINE_PER_PLAYER = pawns
    costanti.FINAL_CELLS = pawns
    costanti.CELLS_PER_ARM = 5
    costanti.PLAYER_COLORS = [_hex_to_rgb(p["hex"]) for p in players_cfg]

    _names_from_config = [p.get("name", f"Giocatore {i+1}")
                          for i, p in enumerate(players_cfg)]
else:
    _names_from_config = None


# =============================================================================
# IMPORTS (costanti già patchate)
# =============================================================================

from costanti import (
    NUM_PLAYERS, PLAYER_COLORS, PEDINE_PER_PLAYER,
    FINAL_CELLS, CELLS_PER_ARM, HOME_OFFSETS,
    SCREEN_SHAKE_AMPLITUDE, SCREEN_SHAKE_TIME, SCREEN_SHAKE_DECAY,
)
from draw import draw_board, polar, player_angle, invalidate_board_cache
from celle import Cella
from pedine import Pedina
from player import Player
from logica import is_pawn_valid
from dado import Dado
from bot_ai import bot_choose_move, BOT_THINK_DELAY, BOT_MOVE_DELAY
from sound import SoundManager
from hud import (
    PlayerNames, TurnBanner, DiceDisplay, Leaderboard,
    MessageBar, Toolbar, SettingsPopup,
    ACTION_SETTINGS, ACTION_RESET, ACTION_QUIT,
    ACTION_GOTO_MENU, ACTION_RESET_GAME, ACTION_TOGGLE_MUTE, ACTION_TOGGLE_MESSAGES, ACTION_CLOSE_POPUP,
    ACTION_TOGGLE_MUTE_SFX, ACTION_TOGGLE_MUTE_MUSIC,
    ACTION_END_GAME,
)

import draw as _draw_mod, hud as _hud_mod
_draw_mod.NUM_PLAYERS = costanti.NUM_PLAYERS
_draw_mod.PLAYER_COLORS = costanti.PLAYER_COLORS
_draw_mod.PEDINE_PER_PLAYER = costanti.PEDINE_PER_PLAYER
_hud_mod.NUM_PLAYERS = costanti.NUM_PLAYERS
_hud_mod.PLAYER_COLORS = costanti.PLAYER_COLORS
_hud_mod.PEDINE_PER_PLAYER = costanti.PEDINE_PER_PLAYER


# =============================================================================
# STATO GLOBALE
# =============================================================================

class TurnPhase(Enum):
    WAITING_FOR_ROLL = auto()
    DICE_ANIMATION = auto()
    WAITING_FOR_MOVE = auto()
    PIECE_ANIMATION = auto()
    MESSAGE_DISPLAY = auto()
    GAME_OVER = auto()

# Dimensioni schermo e geometria
screen_width = screen_height = 900
center_x = center_y = 0.0
center_radius = cell_size = arm_length = cell_radius = margin = None

# Celle del tabellone
path_cells = []
final_paths = {}
path_start_index = {}
home_cells = {}

# Timer globali
timers = {"total": 0.0, "shaking_time": 0.0, "frame_counter": 0}

# Giocatori
players = []
current_player = None
current_phase = TurnPhase.WAITING_FOR_ROLL
dice = None
dice_roll = 0

# Audio offsets
DICE_SOUND_OFFSET = 0.5
DICE_REVEAL_OFFSET = 0.5

# Pending audio/reveal
dice_pending = {
    "timer": 0.0,
    "active": False,
    "roll": 0,
    "is_six": False,
    "sound_played": False,
}

results_played = False

# Bot timing
bot_timer = 0.0
bot_phase_handled = None
piece_anim_started = False

# Fullscreen
is_fullscreen = False

# HUD elements
player_names = turn_banner = dice_display = leaderboard = None
msg_bar = toolbar = settings_popup = None
sfx = None


# =============================================================================
# END SCREEN
# =============================================================================

def show_end_screen():
    """Apre la schermata finale con i risultati."""
    import tkinter as tk
    try:
        from end_screen import EndScreen
    except ImportError:
        print("[ludo] EndScreen non trovata.")
        return

    players_data = []
    for p in players:
        name = player_names.get(p.index) if player_names else f"Giocatore {p.index + 1}"
        color_rgb = costanti.PLAYER_COLORS[p.index]
        hex_color = "#{:02x}{:02x}{:02x}".format(*color_rgb)

        color_name = "Colore"
        if _config.get("players") and p.index < len(_config["players"]):
            color_name = _config["players"][p.index].get("color", color_name)
            if not player_names:
                name = _config["players"][p.index].get("name", name)

        pawns_home = p.count_pedine_in_final()
        pawns_on_board = sum(
            1 for pawn in p.pedine
            if not pawn.current_cell.is_home and not getattr(pawn, 'at_goal', False)
        )
        active_pawns = [pawn for pawn in p.pedine
                       if not pawn.current_cell.is_home
                       and not getattr(pawn, 'at_goal', False)]
        best_steps = max((getattr(pawn, 'steps_total', 0) for pawn in active_pawns), default=0)
        if not active_pawns:
            best_steps = max((getattr(pawn, 'steps_total', 0) for pawn in p.pedine), default=0)

        players_data.append({
            "name": name,
            "color": color_name,
            "hex": hex_color,
            "pawns_home": pawns_home,
            "pawns_on_board": pawns_on_board,
            "best_steps": best_steps,
            "turns": p.turns,
            "bot": getattr(p, 'is_bot', False),
        })

    game_data = {
        "players": players_data,
        "pawns_each": costanti.PEDINE_PER_PLAYER,
    }

    root = tk.Tk()
    EndScreen(root, game_data)
    root.mainloop()


# =============================================================================
# GEOMETRIA
# =============================================================================

def calculate_dimensions():
    """Calcola dimensioni del tabellone in base alla risoluzione."""
    global center_x, center_y, center_radius, cell_size, arm_length, cell_radius, margin
    n = costanti.NUM_PLAYERS
    center_x, center_y = screen_width / 2, screen_height / 2
    margin = min(screen_width, screen_height) / 5
    available = min(screen_width, screen_height) - margin * 2
    center_radius = available * math.sqrt(n * 9) / 35
    cell_size = ((available / 2) - center_radius) / costanti.CELLS_PER_ARM
    arm_length = cell_size * (costanti.CELLS_PER_ARM + 1) + center_radius
    cell_radius = cell_size / 2.3


def get_home_geometry(player_index):
    """Restituisce posizione e dimensione della casa di un giocatore."""
    dx, dy = polar(player_angle(player_index, costanti.NUM_PLAYERS), arm_length * 1.20)
    return center_x + dx, center_y + dy, cell_size * 3


def get_home_slot(hx, hy, size, idx):
    """Calcola posizione di uno slot nella casa."""
    ox, oy = HOME_OFFSETS[idx]
    rad = math.atan2(hy - center_y, hx - center_x)
    px, py = ox * size * 0.6, oy * size * 0.6
    rx = px * math.cos(rad) - py * math.sin(rad)
    ry = px * math.sin(rad) + py * math.cos(rad)
    return int(hx + rx), int(hy + ry)


# =============================================================================
# TABELLONE
# =============================================================================

def iter_board_geometry():
    """Generatore che itera su tutte le celle del tabellone."""
    n = costanti.NUM_PLAYERS
    cpp = costanti.PEDINE_PER_PLAYER
    fc = costanti.FINAL_CELLS
    ca = costanti.CELLS_PER_ARM
    cell_index = 0

    for pi in range(n):
        dx, dy = polar(player_angle(pi, n), 1)
        px, py = -dy, dx
        min_d = center_radius
        max_d = min_d + ca * cell_size

        # Celle finali (dal centro verso l'esterno)
        for i in range(fc):
            yield {"player_index": pi, "index": i, "is_final": True,
                   "x": center_x + dx * (max_d - (i + 1) * cell_size),
                   "y": center_y + dy * (max_d - (i + 1) * cell_size)}

        # Braccio superiore (retrogrado)
        for i in reversed(range(ca)):
            yield {"player_index": pi, "index": cell_index,
                   "x": center_x + dx * (max_d - i * cell_size) - px * cell_size,
                   "y": center_y + dy * (max_d - i * cell_size) - py * cell_size}
            cell_index += 1

        # Cella end
        yield {"player_index": pi, "index": cell_index, "is_end": True,
               "x": center_x + dx * max_d, "y": center_y + dy * max_d}
        cell_index += 1

        # Braccio inferiore (avanti)
        for i in range(ca):
            yield {"player_index": pi, "index": cell_index, "is_start": i == 0,
                   "x": center_x + dx * (max_d - i * cell_size) + px * cell_size,
                   "y": center_y + dy * (max_d - i * cell_size) + py * cell_size}
            cell_index += 1

        # Cella intersection
        dx2, dy2 = polar(player_angle(pi + 0.5, n), 1)
        yield {"player_index": pi, "index": cell_index, "is_intersection": True,
               "x": center_x + dx2 * (min_d + cell_size),
               "y": center_y + dy2 * (min_d + cell_size)}
        cell_index += 1

    # Celle home (slot nelle case)
    for pi in range(n):
        hx, hy, size = get_home_geometry(pi)
        for i in range(cpp):
            x, y = get_home_slot(hx, hy, size, i)
            yield {"player_index": pi, "index": i, "is_home": True, "x": x, "y": y}


def generate_board():
    """Genera tutte le celle del tabellone."""
    global path_cells, final_paths, path_start_index, home_cells
    path_cells = []
    final_paths = {}
    path_start_index = {}
    home_cells = {}

    for data in iter_board_geometry():
        p = data["player_index"]
        if data.get("is_final"):
            c = Cella(data["x"], data["y"], 'final', player=p,
                      index=data["index"], is_final=True)
            final_paths.setdefault(p, []).append(c)
        elif data.get("is_home"):
            c = Cella(data["x"], data["y"], 'home', is_home=True,
                      player=p, index=data["index"])
            home_cells.setdefault(p, []).append(c)
        else:
            c = Cella(data["x"], data["y"], 'path', player=p,
                      is_end=data.get("is_end", False),
                      is_start=data.get("is_start", False),
                      is_intersection=data.get("is_intersection", False))
            c.index = data["index"]
            path_cells.append(c)
            if data.get("is_start"):
                path_start_index[p] = data["index"]

    for player in players:
        for pawn in player:
            pawn.path_cells = path_cells


def adjust_board():
    """Ricalcola posizioni celle dopo resize."""
    n = costanti.NUM_PLAYERS
    pi = 0
    fi = {p: 0 for p in range(n)}
    hi = {p: 0 for p in range(n)}

    for data in iter_board_geometry():
        p = data["player_index"]
        if data.get("is_final"):
            c = final_paths[p][fi[p]]
            fi[p] += 1
        elif data.get("is_home"):
            c = home_cells[p][hi[p]]
            hi[p] += 1
        else:
            c = path_cells[pi]
            pi += 1
        c.x = data["x"]
        c.y = data["y"]

    for player in players:
        for pawn in player:
            pawn.path_cells = path_cells
            p_index = pawn.player.index
            pawn.final_path = final_paths.get(p_index, [])
            pawn.end_cell = next((c for c in path_cells if c.is_end and c.player == p_index), None)


# =============================================================================
# PEDINE
# =============================================================================

def setup_pawns():
    """Inizializza le pedine nella loro casa."""
    all_pawns = [pawn for pl in players for pawn in pl]
    for p, player in enumerate(players):
        fp = final_paths.get(p, [])
        end_cell = next((c for c in path_cells if c.is_end and c.player == p), None)
        for i, pawn in enumerate(player):
            hc = home_cells[p][i]
            pawn.home_cell = hc
            pawn.final_path = fp
            pawn.end_cell = end_cell
            pawn.teleport_to_cell(hc)
            pawn.altre_pedine = all_pawns


def reset_game():
    """Resetta lo stato del gioco per una nuova partita."""
    global current_phase, current_player, dice, dice_roll
    global bot_timer, bot_phase_handled, piece_anim_started
    global is_fullscreen

    current_phase = TurnPhase.WAITING_FOR_ROLL
    current_player = players[0]
    dice = None
    dice_roll = 0
    bot_timer = 0.0
    bot_phase_handled = None
    piece_anim_started = False
    timers["total"] = timers["shaking_time"] = 0.0
    timers["frame_counter"] = 0

    for pl in players:
        pl.has_won = False
        pl.turns = 0
        pl.extra_turn_earned = False

    setup_pawns()
    turn_banner.notify_new_turn(-1)
    msg_bar.push("Partita resettata!")


# =============================================================================
# HELPERS
# =============================================================================

def next_phase(phase):
    """Restituisce la fase successiva."""
    order = [TurnPhase.WAITING_FOR_ROLL, TurnPhase.DICE_ANIMATION,
             TurnPhase.WAITING_FOR_MOVE, TurnPhase.PIECE_ANIMATION,
             TurnPhase.MESSAGE_DISPLAY]
    return order[(order.index(phase) + 1) % len(order)]


def _phase_label(phase):
    """Formato leggibile del nome fase."""
    return str(phase).split('.')[-1].replace('_', ' ')


def execute_move(pawn):
    """Esegue la mossa di una pedina."""
    global current_phase, piece_anim_started
    if pawn.current_cell.is_home:
        pawn.exit()
    else:
        pawn.move_by(dice_roll)
    piece_anim_started = False
    current_phase = next_phase(current_phase)
    for pl in players:
        for p in pl:
            p.indicated = False


def roll_dice():
    """Avvia il lancio del dado."""
    global current_phase, dice, dice_roll
    current_phase = next_phase(current_phase)
    dice_display.notify_hide()

    size = min(center_radius * 1.35, 100)
    angle = math.radians(random.uniform(0, 360))
    dist = math.hypot(screen_width, screen_height) / 2 + size

    dice = Dado(center_x, center_y, size=size)
    dice_roll = random.randint(1, 6)
    dice.lancia(esito=dice_roll,
                start_x=center_x + math.cos(angle) * dist,
                start_y=center_y + math.sin(angle) * dist,
                end_x=center_x, end_y=center_y)

    dice_pending["active"] = True
    dice_pending["timer"] = max(DICE_SOUND_OFFSET, DICE_REVEAL_OFFSET)
    dice_pending["roll"] = dice_roll
    dice_pending["is_six"] = (dice_roll == 6)
    dice_pending["sound_played"] = False


# =============================================================================
# MAIN
# =============================================================================

def main():
    global screen_width, screen_height
    global players, current_player, current_phase, dice, dice_roll
    global player_names, turn_banner, dice_display, leaderboard
    global msg_bar, toolbar, settings_popup
    global bot_timer, bot_phase_handled, piece_anim_started
    global is_fullscreen
    global sfx

    n = costanti.NUM_PLAYERS
    cpp = costanti.PEDINE_PER_PLAYER

    players = [Player(p, timers, cpp) for p in range(n)]
    current_player = players[0]
    current_phase = TurnPhase.WAITING_FOR_ROLL
    results_played = False
    dice_pending["active"] = False
    dice_pending["timer"] = 0.0

    if _config.get("players"):
        for i, pcfg in enumerate(_config["players"]):
            if i < len(players):
                players[i].is_bot = bool(pcfg.get("bot", False))
                players[i].ai_level = pcfg.get("level", "Casuale") or "Casuale"

    player_names = PlayerNames(n)
    turn_banner = TurnBanner()
    dice_display = DiceDisplay()
    leaderboard = Leaderboard()
    msg_bar = MessageBar()
    toolbar = Toolbar()
    settings_popup = SettingsPopup()

    if sfx is None:
        sfx = SoundManager()
        import sound as _sm
        _sm._global_sfx = sfx

    if _names_from_config:
        player_names.set_names(_names_from_config)

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Non t'Arrabbiare")
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(pygame.display.get_wm_info()["window"], 3)
    except Exception:
        pass

    screen_width, screen_height = screen.get_size()

    calculate_dimensions()
    generate_board()
    setup_pawns()

    turn_banner.notify_new_turn(current_player.index)

    clock = pygame.time.Clock()
    running = True
    goto_menu = False

    while running:
        dt = clock.get_time() / 1000.0

        # ============================================================
        # EVENT HANDLING
        # ============================================================
        for event in pygame.event.get():
            if settings_popup.is_open:
                action = settings_popup.handle_event(event)
                if action and sfx:
                    sfx.play("click")
                if action == ACTION_RESET_GAME:
                    reset_game()
                    settings_popup.close()
                elif action == ACTION_GOTO_MENU:
                    settings_popup.close()
                    running = False
                    goto_menu = True
                elif action == ACTION_END_GAME:
                    settings_popup.close()
                    current_phase = TurnPhase.GAME_OVER
                    running = False
                elif action == ACTION_TOGGLE_MUTE:
                    if sfx:
                        sfx.set_muted(settings_popup.muted)
                    msg_bar.push("Audio " + ("OFF" if settings_popup.muted else "ON"))
                elif action == ACTION_TOGGLE_MUTE_SFX:
                    if sfx:
                        sfx.set_muted_sfx(settings_popup.muted_sfx)
                    msg_bar.push("SFX " + ("OFF" if settings_popup.muted_sfx else "ON"))
                elif action == ACTION_TOGGLE_MUTE_MUSIC:
                    if sfx:
                        sfx.set_muted_music(settings_popup.muted_music)
                    msg_bar.push("Musica " + ("OFF" if settings_popup.muted_music else "ON"))
                elif action == ACTION_TOGGLE_MESSAGES:
                    msg_bar.set_enabled(settings_popup.msg_enabled)
                if event.type == pygame.QUIT:
                    running = False
                continue

            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen_width, screen_height = event.w, event.h
                screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
                calculate_dimensions()
                adjust_board()
                invalidate_board_cache()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    settings_popup.open() if not settings_popup.is_open else settings_popup.close()
                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((900, 900), pygame.RESIZABLE)
                    screen_width, screen_height = screen.get_size()
                    calculate_dimensions()
                    adjust_board()
                    invalidate_board_cache()
                elif (event.key == pygame.K_SPACE
                        and current_phase == TurnPhase.WAITING_FOR_ROLL
                        and not current_player.is_bot):
                    roll_dice()

            action = toolbar.handle_event(event)
            if action and sfx:
                sfx.play("click")
            if action == ACTION_SETTINGS:
                settings_popup.open()
            elif action == ACTION_RESET:
                reset_game()
            elif action == ACTION_QUIT:
                running = False

        # ============================================================
        # UPDATE TIMERS
        # ============================================================
        timers["total"] += dt
        timers["frame_counter"] += 1

        if timers["shaking_time"] > 0:
            angle = math.radians(random.uniform(0, 360))
            decay = math.exp(-SCREEN_SHAKE_DECAY *
                  (SCREEN_SHAKE_TIME - timers["shaking_time"]) / SCREEN_SHAKE_TIME)
            screen_shake_x = math.sin(angle) * SCREEN_SHAKE_AMPLITUDE * decay
            screen_shake_y = math.cos(angle) * SCREEN_SHAKE_AMPLITUDE * decay
            timers["shaking_time"] -= dt
        else:
            screen_shake_x = screen_shake_y = 0

        turn_banner.update(dt)
        dice_display.update(dt)
        msg_bar.update(dt)
        settings_popup.update(dt)
        if sfx:
            sfx.update()

        # ============================================================
        # PENDING DICE AUDIO/REVEAL
        # ============================================================
        if dice_pending["active"]:
            dice_pending["timer"] -= dt
            t = dice_pending["timer"]
            r = dice_pending["roll"]
            sound_threshold = max(DICE_SOUND_OFFSET, DICE_REVEAL_OFFSET) - DICE_SOUND_OFFSET
            if sfx and not dice_pending["sound_played"] and t <= sound_threshold:
                sfx.play("dice")
                if dice_pending["is_six"]:
                    sfx.play("roll_6")
                dice_pending["sound_played"] = True
            if t <= 0.0:
                name = player_names.get(current_player.index)
                dice_display.notify_roll(r)
                if dice_pending["is_six"]:
                    msg_bar.push(f" {name} Mossa bonus!")
                dice_pending["active"] = False

        num_players = costanti.NUM_PLAYERS

        # ============================================================
        # BOT AI LOGIC
        # ============================================================
        if (current_player.is_bot
                and not settings_popup.is_open
                and current_phase in (TurnPhase.WAITING_FOR_ROLL,
                                       TurnPhase.WAITING_FOR_MOVE)):
            if current_phase == TurnPhase.WAITING_FOR_ROLL:
                if bot_phase_handled != TurnPhase.WAITING_FOR_ROLL:
                    bot_timer = BOT_THINK_DELAY
                    bot_phase_handled = TurnPhase.WAITING_FOR_ROLL
                else:
                    bot_timer -= dt
                    if bot_timer <= 0:
                        bot_phase_handled = None
                        roll_dice()

            elif current_phase == TurnPhase.WAITING_FOR_MOVE:
                if bot_phase_handled != TurnPhase.WAITING_FOR_MOVE:
                    bot_timer = BOT_MOVE_DELAY
                    bot_phase_handled = TurnPhase.WAITING_FOR_MOVE
                else:
                    bot_timer -= dt
                    if bot_timer <= 0:
                        bot_phase_handled = None
                        chosen = bot_choose_move(
                            current_player, players, dice_roll,
                            path_cells, final_paths)
                        if chosen:
                            execute_move(chosen)
                        else:
                            piece_anim_started = False
                            current_phase = next_phase(current_phase)
        elif current_phase in (TurnPhase.WAITING_FOR_ROLL,
                                TurnPhase.WAITING_FOR_MOVE):
            bot_phase_handled = None

        # ============================================================
        # GAME PHASES
        # ============================================================
        if current_phase == TurnPhase.GAME_OVER:
            if sfx and not results_played:
                sfx.play("results")
                results_played = True
            running = False

        elif current_phase == TurnPhase.DICE_ANIMATION and dice:
            dice.update(dt)
            if dice.is_finished():
                current_phase = next_phase(current_phase)
                all_p = [p for pl in players for p in pl]
                valid = [p for p in all_p if is_pawn_valid(
                    p, players, current_player.index, dice_roll, path_cells, final_paths)]
                if not valid:
                    msg_bar.push("Nessuna mossa valida!")
                    if sfx:
                        sfx.play("pass")
                    current_phase = TurnPhase.MESSAGE_DISPLAY
                elif len(valid) == 1 and not current_player.is_bot:
                    name = player_names.get(current_player.index)
                    msg_bar.push(f"Mossa obbligata per {name}!")
                    execute_move(valid[0])
                else:
                    if not current_player.is_bot:
                        msg_bar.push("Seleziona una pedina")

        elif current_phase == TurnPhase.PIECE_ANIMATION:
            if not piece_anim_started:
                all_p_anim = [p for pl in players for p in pl]
                for pawn in all_p_anim:
                    pawn.update(dt)
                if any(pawn.is_animating() for pawn in all_p_anim):
                    piece_anim_started = True
                elif any(pawn.step_left > 0 for pawn in all_p_anim):
                    pass
                else:
                    piece_anim_started = True
            else:
                for pl in players:
                    for pawn in pl:
                        pawn.update(dt)
                if not any(pawn.is_animating() for pl in players for pawn in pl):
                    piece_anim_started = False
                    if current_player.check_victory():
                        name = player_names.get(current_player.index)
                        msg_bar.push(f" {name} ha vinto la partita!")
                        current_phase = TurnPhase.GAME_OVER
                    else:
                        current_phase = TurnPhase.MESSAGE_DISPLAY

        elif current_phase == TurnPhase.WAITING_FOR_MOVE and not current_player.is_bot:
            all_p = [p for pl in players for p in pl]
            for pawn in all_p:
                pawn.indicated = is_pawn_valid(
                    pawn, players, current_player.index, dice_roll, path_cells, final_paths)
            mouse = pygame.mouse.get_pos()
            hov = None
            min_dist = cell_size
            for pawn in all_p:
                pawn.hovered = False
                d = math.hypot(pawn.current_cell.x - mouse[0], pawn.current_cell.y - mouse[1])
                if d < min_dist:
                    min_dist = d
                    hov = pawn
            if hov:
                hov.hovered = True
                if hov.indicated and pygame.mouse.get_pressed()[0]:
                    execute_move(hov)

        elif current_phase == TurnPhase.MESSAGE_DISPLAY:
            if current_player.check_victory():
                name = player_names.get(current_player.index)
                msg_bar.push(f" {name} ha vinto la partita!")
                current_phase = TurnPhase.GAME_OVER
            else:
                bonus = current_player.extra_turn_earned
                if dice_roll == 6 or bonus:
                    if bonus:
                        msg_bar.push(f" {player_names.get(current_player.index)} ha mangiato - Mossa bonus!")
                    current_player.extra_turn_earned = False
                else:
                    current_player.turns += 1
                    current_player = players[(current_player.index + 1) % num_players]
                    turn_banner.notify_new_turn(current_player.index)
                    if sfx:
                        sfx.play("turn")
                    msg_bar.push(f"Turno di {player_names.get(current_player.index)}")
                current_phase = next_phase(current_phase)

        # ============================================================
        # RENDER
        # ============================================================
        draw_board(screen, center_x, center_y, center_radius, cell_size, arm_length,
                   path_cells, final_paths, home_cells, players,
                   get_home_geometry, cell_radius, current_player.index,
                   dice, screen_shake_x, screen_shake_y, dt)
        leaderboard.draw(screen, players, player_names, current_player.index, screen_height)
        turn_banner.draw(screen, current_player.index, _phase_label(current_phase),
                        player_names.get(current_player.index), screen_width)
        dice_display.draw(screen, dice_roll, screen_width)
        toolbar.draw(screen, screen_width)
        msg_bar.draw(screen, screen_width, screen_height)
        settings_popup.draw(screen, screen_width, screen_height)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

    if goto_menu:
        import subprocess as _sp, os as _os
        _sp.Popen([sys.executable,
                   _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                 "start_screen.py")])
    elif current_phase == TurnPhase.GAME_OVER:
        show_end_screen()

    sys.exit()


if __name__ == "__main__":
    main()
