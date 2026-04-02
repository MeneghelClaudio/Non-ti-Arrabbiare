"""
pedine.py - Classe Pedina e logica di movimento
==============================================

Una Pedina rappresenta un singolo pezzo da gioco.
Gestisce movimento, animazione, e interazioni con altre pedine.
"""

import math
from celle import get_start_for_player
from costanti import *
from draw import draw_circle, adjust_color, draw_triangle

# Riferimento al SoundManager - impostato da sound.py all'avvio
_sfx_instance = None


class Pedina:
    """
    Rappresenta una pedina nel gioco.
    
    Attributi principali:
        player: riferimento al Player proprietario
        current_cell: Cella dove si trova la pedina
        home_cell: Cella slot nella casa del giocatore
        final_path: lista delle celle finali assegnate al giocatore
        end_cell: cella is_end del giocatore (ingresso al percorso finale)
        at_goal: True se la pedina è arrivata al traguardo
        goal_cell: cella finale assegnata a questa pedina (slot unico)
        steps_total: passi totali percorsi dall'uscita di casa
        anim_progress: progresso dell'animazione corrente (0.0 - 1.0)
        step_left: passi ancora da compiere nel movimento corrente
        indicated: True se la pedina può essere mossa (evidenziata)
        hovered: True se il mouse è sopra la pedina
    """
    
    def __init__(self, player, timers):
        self.player = player
        self.indicated = False
        self.hovered = False

        self.timers = timers
        self.path_cells = []
        self.altre_pedine = []

        self.home_cell = None
        self.old_cell = None
        self.current_cell = None
        self.final_path = []
        self.end_cell = None
        self.at_goal = False
        self.goal_cell = None
        self.steps_total = 0

        self.anim_progress = 1.0
        self.anim_delay = 0.0
        self.step_left = 0

    # =========================================================================
    # MOVIMENTO
    # =========================================================================

    def move_to(self, new_cell):
        """Sposta la pedina a una nuova cella (avvia animazione)."""
        self.old_cell = self.current_cell
        self.current_cell = new_cell
        self.anim_progress = 0.0

    def move_by(self, steps):
        """Avvia il movimento per un dato numero di passi."""
        self.step_left = steps

    def teleport_to_cell(self, new_cell):
        """
        Sposta istantaneamente la pedina a una cella (teleport).
        Usato quando viene mangiata e torna a casa.
        """
        self.old_cell = new_cell
        self.current_cell = new_cell
        self.anim_progress = 1.0
        self.anim_delay = 0.0
        self.at_goal = False
        self.goal_cell = None
        self.steps_total = 0
        self.on_landing(self.old_cell, self.current_cell)

    def exit(self):
        """
        Fa uscire la pedina dalla casa verso la cella di start.
        """
        if self.current_cell and self.current_cell.is_home:
            start_cell = get_start_for_player(self.player.index, self.path_cells)
            if start_cell:
                self.steps_total = 0
                if _sfx_instance:
                    _sfx_instance.play("leave_home")
                self.move_to(start_cell)

    def step_forward(self):
        """
        Avanza la pedina di una cella.
        Gestisce i casi speciali: percorso finale, arrivo al traguardo.
        """
        if self.current_cell is None:
            return

        if self.at_goal:
            # Già al traguardo: non si muove più
            self.step_left = 0
            return

        # Caso 1: già nel percorso finale
        if self.current_cell.is_final and self.current_cell in self.final_path:
            if self.goal_cell is None:
                self.goal_cell = compute_goal_cell(self)
            
            idx = self.final_path.index(self.current_cell)
            goal_idx = self.final_path.index(self.goal_cell)

            if idx < goal_idx:
                self.steps_total += 1
                self.move_to(self.final_path[idx + 1])
            else:
                # Raggiunto lo slot assegnato
                self.step_left = 0
                self.at_goal = True
            return

        # Caso 2: sulla cella is_end: entra nel percorso finale
        if (self.current_cell.is_end and
                self.current_cell.player == self.player.index and
                self.final_path):
            if self.goal_cell is None:
                self.goal_cell = compute_goal_cell(self)
            self.steps_total += 1
            self.move_to(self.final_path[0])
            return

        # Caso 3: percorso principale - avanza di uno
        current_index = self.path_cells.index(self.current_cell)
        next_index = (current_index + 1) % len(self.path_cells)
        next_cell = self.path_cells[next_index]
        self.steps_total += 1
        self.move_to(next_cell)

    # =========================================================================
    # ANIMAZIONE
    # =========================================================================

    def update(self, dt):
        """
        Aggiorna l'animazione della pedina ogni frame.
        
        Args:
            dt: delta time in secondi
        """
        if self.is_animating():
            self.update_animation(PEDINE_SPEED, dt)
        if not self.is_animating() and self.step_left > 0:
            self.step_left -= 1
            self.step_forward()

    def update_animation(self, speed, dt):
        """Aggiorna il progresso dell'animazione di movimento."""
        prev = self.anim_progress
        self.anim_progress = min(self.anim_progress + speed * dt, 1.0)
        self.anim_delay = max(self.anim_delay - dt, 0.0)

        if prev < 1.0 and self.anim_progress >= 1.0:
            # Animazione completata
            self.old_cell = self.current_cell
            self.anim_delay = ANIMATION_DELAY
            if _sfx_instance:
                _sfx_instance.play("step")
            self.on_landing(self.old_cell, self.current_cell)

    def is_animating(self):
        """True se l'animazione è in corso."""
        return not (self.anim_progress >= 1.0 and self.anim_delay <= 0.0)

    def _get_animation_state(self, cell_size):
        """
        Calcola lo stato di rendering per l'animazione 3D.
        
        Returns:
            Dizionario con x, y, y_3d (altezza), r (raggio), offset, max_offset
        """
        if self.current_cell is None:
            return None

        r = cell_size / 2.4
        # Posizione precedente (o attuale se non c'è)
        ox, oy = ((self.old_cell.x, self.old_cell.y)
                  if self.old_cell else (self.current_cell.x, self.current_cell.y))
        cx, cy = self.current_cell.x, self.current_cell.y

        # Interpolazione lineare tra vecchia e nuova posizione
        x = ox + (cx - ox) * self.anim_progress
        y = oy + (cy - oy) * self.anim_progress

        # Effetto salto 3D: picco a metà animazione
        max_offset = r * PEDINE_JUMP_HEIGHT
        offset = max_offset * math.sin(math.pi * self.anim_progress)
        y_3d = y - offset

        return {'x': x, 'y': y, 'y_3d': y_3d, 'r': r,
                'offset': offset, 'max_offset': max_offset}

    # =========================================================================
    # DISEGNO
    # =========================================================================

    def draw(self, screen, cell_size):
        """Disegna la pedina sullo schermo con effetto 3D."""
        state = self._get_animation_state(cell_size)
        if not state:
            return

        x, y, y_3d, r = state['x'], state['y'], state['y_3d'], state['r']
        base_color = PLAYER_COLORS[self.player.index]

        # Corpo: base scura per profondità
        draw_circle(screen, (int(x), int(y_3d)),
                    int(r), adjust_color(base_color, DARKER))

        # Disco superiore con colore base
        r_top = r * 0.78
        draw_circle(screen, (int(x), int(y_3d - r / 1.3)),
                    int(r_top), base_color)

        # Highlight bianco parziale
        highlight_color = adjust_color(base_color, +90)
        r_hl = r_top * 0.42
        ox_hl = -r_top * 0.22
        oy_hl = -r_top * 0.28
        draw_circle(screen,
                    (int(x + ox_hl), int(y_3d - r / 1.3 + oy_hl)),
                    int(r_hl), highlight_color, border_width=0)

    def draw_indicator(self, screen, cell_size):
        """
        Disegna il triangolo indicatore sopra la pedina selezionabile.
        """
        if not self.indicated:
            return

        state = self._get_animation_state(cell_size)
        if not state:
            return

        x, y_3d, r = state['x'], state['y_3d'], state['r']
        base_color = PLAYER_COLORS[self.player.index]
        
        # Oscillazione verticale del triangolo
        altitude = -r * (4 + 0.7 * math.sin(self.timers["total"] * 4))
        s = 1 if not self.hovered else 1.75  # Più grande se in hover
        half_base = r * s
        h = (3 ** 0.5) * half_base  # Altezza triangolo equilatero

        points = [
            (x,              y_3d + h / 2 + altitude),
            (x - half_base,  y_3d - h / 2 + altitude),
            (x + half_base,  y_3d - h / 2 + altitude),
        ]

        draw_triangle(screen, points, base_color, BLACK, 1)

    # =========================================================================
    # INTERAZIONI CON ALTRE PEDINE
    # =========================================================================

    def on_landing(self, old_cell, current_cell):
        """
        Chiamato quando la pedina termina un passo.
        Controlla: arrivo al traguardo, mangiare altre pedine.
        """
        # Controlla se ha raggiunto il traguardo
        goal = self.goal_cell if self.goal_cell is not None else (
            self.final_path[-1] if self.final_path else None)
        if (goal is not None and
                current_cell.is_final and
                current_cell == goal):
            self.at_goal = True
            self.step_left = 0
            if _sfx_instance:
                _sfx_instance.play("destination")
            return  # Non mangia pedine nel traguardo

        if self.step_left == 0:
            # Controlla se ci sono pedine nemiche da mangiare
            pedine_mangiate = current_cell.get_pedine_in_cell(self.altre_pedine)
            for pm in pedine_mangiate:
                if pm.player.index != self.player.index:
                    # Shake schermo + suono
                    self.timers["shaking_time"] = SCREEN_SHAKE_TIME
                    if _sfx_instance:
                        _sfx_instance.play("eat")
                    pm.mangia()
                    # Turno bonus per aver mangiato
                    self.player.extra_turn_earned = True

    def mangia(self):
        """
        La pedina viene mangiata: torna alla casa e resetta stato.
        """
        self.at_goal = False
        self.goal_cell = None
        self.steps_total = 0
        self.move_to(self.home_cell)


def compute_goal_cell(pedina):
    """
    Restituisce lo slot del final_path assegnato a questa pedina.
    
    Algoritmo: la prima pedina che arriva prende la cella più vicina
    al centro (l'ultima nel final_path), la seconda la penultima, ecc.
    Usa id() per confrontare i riferimenti delle celle.
    
    Args:
        pedina: la Pedina che richiede uno slot
        
    Returns:
        La Cella goal assegnata
    """
    fp = pedina.final_path
    if not fp:
        return fp[-1] if fp else None
    
    # Slot già riservati dalle altre pedine dello stesso giocatore
    reserved = set()
    for ped in pedina.altre_pedine:
        if ped is not pedina and ped.player.index == pedina.player.index:
            gc = getattr(ped, 'goal_cell', None)
            if gc is not None:
                reserved.add(id(gc))
    
    # Assegna lo slot più in fondo libero
    for cell in reversed(fp):
        if id(cell) not in reserved:
            return cell
    return fp[-1]  # fallback
