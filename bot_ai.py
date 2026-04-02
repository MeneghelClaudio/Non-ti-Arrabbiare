"""
bot_ai.py - Intelligenza artificiale per i bot
==============================================

Livelli disponibili:
  Scimmia   – random, mangia sempre se possibile
  Lepre     – porta avanti 1 pedina alla volta, mantiene almeno 2 fuori
  Tartaruga – porta avanti tutte le pedine insieme
  Leone     – cacciatore aggressivo: mangia sempre, insegue i nemici più avanzati,
              fa predict con dado=6, evita celle pericolose
  Stratega  – AI adattiva con punteggio euristico multi-fattore e pesi dinamici
              in base alla fase di gioco

Costanti di tempo:
  BOT_THINK_DELAY – secondi di attesa prima del lancio dado
  BOT_MOVE_DELAY  – secondi di attesa prima della scelta pedina
"""

import random
from logica import simulate_move, is_pawn_valid

# Tempi configurabili
BOT_THINK_DELAY = 0.9   # sec prima del lancio dado
BOT_MOVE_DELAY = 0.55   # sec prima della scelta pedina

# =============================================================================
# FUNZIONI DI SUPPORTO (usate da tutte le AI)
# =============================================================================

def get_valid_pawns(player, players, dice_roll, path_cells, final_paths):
    """
    Restituisce la lista delle pedine del giocatore che possono muoversi.
    
    Args:
        player: il Player corrente
        players: tutti i giocatori
        dice_roll: valore del dado
        path_cells: celle del percorso principale
        final_paths: dict {player_index: [celle_finali]}
        
    Returns:
        Lista di Pedina valid
    """
    return [p for p in player.pedine
            if is_pawn_valid(p, players, player.index, dice_roll,
                            path_cells, final_paths)]


def get_eating_pawns(valid_pawns, dice_roll, path_cells, final_paths, current_player_index):
    """
    Tra le pedine valide, restituisce quelle che possono mangiare un nemico.
    
    Args:
        valid_pawns: lista delle pedine che possono muoversi
        dice_roll: valore del dado
        path_cells: celle del percorso principale
        final_paths: dict {player_index: [celle_finali]}
        current_player_index: indice del giocatore corrente
        
    Returns:
        Lista di Pedina che possono mangiare
    """
    result = []
    for pawn in valid_pawns:
        if pawn.current_cell.is_home:
            continue
        target = simulate_move(pawn, dice_roll, path_cells, final_paths)
        if target is None:
            continue
        for other in pawn.altre_pedine:
            if (other.player.index != current_player_index
                    and other.current_cell == target
                    and not other.current_cell.is_home
                    and not getattr(other, 'at_goal', False)):
                result.append(pawn)
                break
    return result


def position_score(pawn):
    """
    Punteggio di avanzamento: più alto = più avanzata.
    Pedine in casa = -1 (non sono ancora uscite).
    Pedine al traguardo = infinito.
    """
    if pawn.current_cell.is_home:
        return -1
    if getattr(pawn, 'at_goal', False):
        return float('inf')
    return pawn.steps_total


def sort_by_position(pawns, most_advanced_first=True):
    """Ordina le pedine per posizione."""
    return sorted(pawns, key=position_score, reverse=most_advanced_first)


def steps_to_nearest_enemy(pawn, landing_cell, path_cells):
    """
    Distanza in passi dalla cella di atterraggio al nemico più vicino davanti.
    
    Args:
        pawn: pedina che si muove
        landing_cell: cella di destinazione
        path_cells: celle del percorso principale
        
    Returns:
        Distanza in passi, o inf se nessun nemico raggiungibile
    """
    if landing_cell is None or landing_cell.is_final:
        return float('inf')

    # Nemici sul percorso (non in casa, non al traguardo)
    enemies = [p for p in pawn.altre_pedine
               if p.player.index != pawn.player.index
               and not p.current_cell.is_home
               and not getattr(p, 'at_goal', False)
               and not p.current_cell.is_final]

    if not enemies:
        return float('inf')

    try:
        landing_idx = path_cells.index(landing_cell)
    except ValueError:
        return float('inf')

    min_dist = float('inf')
    for enemy in enemies:
        try:
            enemy_idx = path_cells.index(enemy.current_cell)
        except ValueError:
            continue
        # Distanza in avanti (circolare)
        dist = (enemy_idx - landing_idx) % len(path_cells)
        if dist == 0:
            dist = len(path_cells)  # È già lì
        min_dist = min(min_dist, dist)

    return min_dist


def cell_danger(landing_cell, player_index, all_pawns, path_cells, final_paths):
    """
    Stima il pericolo di una cella: conta quanti nemici
    possono raggiungerla con un dado da 1 a 6.
    
    Args:
        landing_cell: cella di destinazione
        player_index: indice del giocatore
        all_pawns: tutte le pedine
        path_cells: celle del percorso principale
        final_paths: dict {player_index: [celle_finali]}
        
    Returns:
        Numero di nemici che possono mangiare (0-6)
    """
    if landing_cell is None:
        return 0
    if getattr(landing_cell, 'is_final', False):
        return 0

    try:
        target_idx = path_cells.index(landing_cell)
    except ValueError:
        return 0

    danger = 0
    n = len(path_cells)
    for pawn in all_pawns:
        if pawn.player.index == player_index:
            continue
        if pawn.current_cell.is_home or getattr(pawn, 'at_goal', False):
            continue
        if getattr(pawn.current_cell, 'is_final', False):
            continue
        try:
            pawn_idx = path_cells.index(pawn.current_cell)
        except ValueError:
            continue
        # Distanza in avanti dal nemico alla nostra cella target
        dist = (target_idx - pawn_idx) % n
        if 1 <= dist <= 6:
            danger += 1

    return danger


def all_pawns_list(players):
    """Restituisce una lista piatta di tutte le pedine."""
    result = []
    for pl in players:
        result.extend(pl.pedine)
    return result


def get_start_cell(player_index, path_cells):
    """Restituisce la cella di spawn per il giocatore."""
    try:
        from celle import get_start_for_player
        return get_start_for_player(player_index, path_cells)
    except Exception:
        return None


# =============================================================================
# AI: SCIMMIA (random, mangia sempre se può)
# =============================================================================

def ai_monkey(player, players, dice_roll, path_cells, final_paths):
    """
    Strategia:
      - Mangia sempre se possibile (scelta random tra quelle che mangiano)
      - Con dado=6 e pedine sia in casa che fuori: scelta casuale
      - Altrimenti: muove una pedina valida a caso
    """
    valid = get_valid_pawns(player, players, dice_roll, path_cells, final_paths)
    if not valid:
        return None

    # Priorità 1: mangia
    eating = get_eating_pawns(valid, dice_roll, path_cells, final_paths, player.index)
    if eating:
        return random.choice(eating)

    # Con dado=6 e pedine sia in casa che fuori: scelta casuale
    if dice_roll == 6:
        home_valid = [p for p in valid if p.current_cell.is_home]
        nonhome_valid = [p for p in valid if not p.current_cell.is_home]
        if home_valid and nonhome_valid:
            return random.choice(random.choice([home_valid, nonhome_valid]))

    return random.choice(valid)


# =============================================================================
# AI: LEPRE (porta avanti 1 pedina alla volta)
# =============================================================================

def ai_hare(player, players, dice_roll, path_cells, final_paths):
    """
    Strategia:
      - Mantiene almeno 2 pedine fuori: esce solo se ne ha < 2
      - Mangia sempre se possibile
      - Muove sempre la pedina più avanzata
    """
    valid = get_valid_pawns(player, players, dice_roll, path_cells, final_paths)
    if not valid:
        return None

    # Priorità 1: mangia
    eating = get_eating_pawns(valid, dice_roll, path_cells, final_paths, player.index)
    if eating:
        return sort_by_position(eating, most_advanced_first=True)[0]

    pawns_out = [p for p in player.pedine
                 if not p.current_cell.is_home
                 and not getattr(p, 'at_goal', False)]
    home_valid = [p for p in valid if p.current_cell.is_home]
    nonhome_valid = [p for p in valid if not p.current_cell.is_home]

    # Priorità 2: con dado=6, esci se hai < 2 pedine fuori
    if dice_roll == 6 and home_valid and len(pawns_out) < 2:
        return home_valid[0]

    # Priorità 3: avanza la pedina più avanzata
    if nonhome_valid:
        return sort_by_position(nonhome_valid, most_advanced_first=True)[0]

    if home_valid:
        return home_valid[0]

    return random.choice(valid)


# =============================================================================
# AI: TARTARUGA (porta avanti tutte le pedine insieme)
# =============================================================================

def ai_turtle(player, players, dice_roll, path_cells, final_paths):
    """
    Strategia:
      - Esce sempre una nuova pedina con dado=6
      - Mangia sempre se possibile, preferendo il nemico più indietro
      - Muove sempre la pedina più indietro (porta il gruppo compatto)
    """
    valid = get_valid_pawns(player, players, dice_roll, path_cells, final_paths)
    if not valid:
        return None

    # Priorità 1: mangia
    eating = get_eating_pawns(valid, dice_roll, path_cells, final_paths, player.index)
    if eating:
        return sort_by_position(eating, most_advanced_first=False)[0]

    home_valid = [p for p in valid if p.current_cell.is_home]
    nonhome_valid = [p for p in valid if not p.current_cell.is_home]

    # Priorità 2: con dado=6, esci
    if dice_roll == 6 and home_valid:
        return home_valid[0]

    # Priorità 3: avanza la pedina più indietro
    if nonhome_valid:
        return sort_by_position(nonhome_valid, most_advanced_first=False)[0]

    if home_valid:
        return home_valid[0]

    return random.choice(valid)


# =============================================================================
# AI: LEONE (cacciatore aggressivo)
# =============================================================================

def _leone_predict_bonus(landing_cell, path_cells, all_pawns, player_index):
    """
    Dato=6: stima il valore del turno bonus dopo essersi mossi.
    Restituisce il punteggio del nemico più avanzato raggiungibile con dado 1-6.
    """
    if landing_cell is None or getattr(landing_cell, 'is_final', False):
        return 0

    try:
        land_idx = path_cells.index(landing_cell)
    except ValueError:
        return 0

    n = len(path_cells)
    best_prey_score = 0

    for d in range(1, 7):
        candidate_cell = path_cells[(land_idx + d) % n]
        for pawn in all_pawns:
            if (pawn.player.index != player_index
                    and pawn.current_cell == candidate_cell
                    and not pawn.current_cell.is_home
                    and not getattr(pawn, 'at_goal', False)
                    and not getattr(pawn.current_cell, 'is_final', False)):
                prey_score = max(position_score(pawn), 0)
                if prey_score > best_prey_score:
                    best_prey_score = prey_score

    # Penalità se la cella è pericolosa
    danger = cell_danger(landing_cell, player_index, all_pawns, path_cells, [])
    penalty = danger * 15

    return max(0, best_prey_score - penalty)


def ai_lion(player, players, dice_roll, path_cells, final_paths):
    """
    Strategia aggressiva:
      1. Mangia il nemico più avanzato
      2. Con dado=6: predict per posizionarsi
      3. Evita celle pericolose
      4. Insegue il nemico più avanzato in classifica
    """
    valid = get_valid_pawns(player, players, dice_roll, path_cells, final_paths)
    if not valid:
        return None
    
    all_pawns = all_pawns_list(players)

    # 1. Mangia il nemico più avanzato
    eating = get_eating_pawns(valid, dice_roll, path_cells, final_paths, player.index)
    if eating:
        best_pawn = None
        best_score = -1
        for pawn in eating:
            target = simulate_move(pawn, dice_roll, path_cells, final_paths)
            if target is None:
                continue
            for enemy in all_pawns:
                if (enemy.player.index != player.index
                        and enemy.current_cell == target
                        and not enemy.current_cell.is_home
                        and not getattr(enemy, 'at_goal', False)):
                    score = position_score(enemy)
                    if score > best_score:
                        best_score = score
                        best_pawn = pawn
        return best_pawn or eating[0]
 
    home_valid = [p for p in valid if p.current_cell.is_home]
    nonhome_valid = [p for p in valid if not p.current_cell.is_home]
 
    # 2. Dado=6: predict
    if dice_roll == 6:
        predict_scores = {}
        for pawn in valid:
            if pawn.current_cell.is_home:
                start_cell = get_start_cell(player.index, path_cells)
                if start_cell is None:
                    continue
                own_on_start = any(
                    p.current_cell == start_cell
                    for p in player.pedine
                    if not p.current_cell.is_home
                )
                if own_on_start:
                    continue
                landing = start_cell
            else:
                landing = simulate_move(pawn, dice_roll, path_cells, final_paths)
 
            bonus = _leone_predict_bonus(landing, path_cells, all_pawns, player.index)
            predict_scores[pawn] = bonus
 
        if predict_scores:
            best_pawn = max(predict_scores, key=lambda p: predict_scores[p])
            best_bonus = predict_scores[best_pawn]
            PREDICT_THRESHOLD = 5
            if best_bonus >= PREDICT_THRESHOLD:
                return best_pawn
 
    # 3. Filtra celle pericolose
    def danger(pawn):
        landing = simulate_move(pawn, dice_roll, path_cells, final_paths)
        return cell_danger(landing, player.index, all_pawns, path_cells, final_paths)
 
    safe_moves = [p for p in nonhome_valid if danger(p) < 2]
    candidates = safe_moves if safe_moves else nonhome_valid
 
    # 4. Insegue il nemico più avanzato
    if candidates:
        enemies_in_play = [p for p in all_pawns
                           if p.player.index != player.index
                           and not p.current_cell.is_home
                           and not getattr(p, 'at_goal', False)
                           and not getattr(p.current_cell, 'is_final', False)]
 
        if enemies_in_play:
            prime_target = max(enemies_in_play, key=position_score)
            try:
                target_idx = path_cells.index(prime_target.current_cell)
                n = len(path_cells)
 
                def dist_to_prime(pawn):
                    landing = simulate_move(pawn, dice_roll, path_cells, final_paths)
                    if landing is None or getattr(landing, 'is_final', False):
                        return float('inf')
                    try:
                        land_idx = path_cells.index(landing)
                    except ValueError:
                        return float('inf')
                    return (target_idx - land_idx) % n
 
                return min(candidates, key=dist_to_prime)
            except ValueError:
                pass
 
        return sort_by_position(candidates, most_advanced_first=True)[0]
 
    if home_valid:
        return home_valid[0]
    return random.choice(valid)


# =============================================================================
# AI: STRATEGA (euristico adattivo multi-fattore)
# =============================================================================

# Pesi base dei fattori di valutazione
_W_EAT_BASE = 500
_W_ENTER_FINAL = 300
_W_ADVANCE = 5
_W_EXIT_HOME = 80
_W_DANGER = -150
_W_SAFE_BONUS = 60
_W_PREDICT_6 = 40


def _game_phase(player, players):
    """
    Restituisce la fase di gioco dal punto di vista del giocatore:
      'early' – 0-1 pedine fuori
      'mid'   – 2-3 pedine fuori
      'late'  – pedine vicine al traguardo
    """
    fuori = [p for p in player.pedine
             if not p.current_cell.is_home
             and not getattr(p, 'at_goal', False)]
    n_fuori = len(fuori)
 
    if n_fuori <= 1:
        return 'early'
 
    advanced = [p for p in fuori
                if not getattr(p.current_cell, 'is_final', False)
                and p.steps_total > 40]
    if len(advanced) >= 2:
        return 'late'
 
    return 'mid'


def _phase_weights(phase):
    """
    Moltiplicatori sui pesi base in base alla fase di gioco.
    """
    if phase == 'early':
        return {
            'eat': 1.2, 'enter': 1.0, 'advance': 1.2,
            'exit': 2.0, 'danger': 0.5, 'safe': 0.8, 'predict': 1.0,
        }
    elif phase == 'late':
        return {
            'eat': 0.9, 'enter': 2.5, 'advance': 1.5,
            'exit': 0.3, 'danger': 2.0, 'safe': 2.0, 'predict': 1.2,
        }
    else:
        return {
            'eat': 1.0, 'enter': 1.5, 'advance': 1.0,
            'exit': 1.0, 'danger': 1.0, 'safe': 1.0, 'predict': 1.0,
        }


def _expected_reroll_value(player, players, path_cells, final_paths):
    """
    Stima del valore atteso del rilancio con dado=6.
    """
    total = 0.0
    count = 0
    for d in range(1, 7):
        v = get_valid_pawns(player, players, d, path_cells, final_paths)
        if not v:
            continue
        eating = get_eating_pawns(v, d, path_cells, final_paths, player.index)
        if eating:
            total += 80
        else:
            best = sort_by_position(
                [p for p in v if not p.current_cell.is_home],
                most_advanced_first=True
            )
            total += d * 5 if best else 0
        count += 1
    return (total / count) if count else 0


def _score_move(pawn, dice_roll, player, players, path_cells, final_paths,
                all_pawns, phase, mults):
    """
    Calcola il punteggio euristico per una mossa.
    Più alto = meglio.
    """
    score = 0.0
 
    is_from_home = pawn.current_cell.is_home
    is_from_final = getattr(pawn.current_cell, 'is_final', False)
 
    # Pedina in casa
    if is_from_home:
        start_cell = get_start_cell(player.index, path_cells)
        if start_cell is None:
            return -9999
        danger = cell_danger(start_cell, player.index, all_pawns, path_cells, final_paths)
        score += _W_EXIT_HOME * mults['exit']
        score += danger * _W_DANGER * mults['danger']
        if dice_roll == 6:
            reroll_val = _expected_reroll_value(player, players, path_cells, final_paths)
            score += reroll_val * (_W_PREDICT_6 / 100.0) * mults['predict']
        return score
 
    # Pedina già nel percorso finale
    if is_from_final:
        try:
            landing = simulate_move(pawn, dice_roll, path_cells, final_paths)
        except (ValueError, Exception):
            return dice_roll * _W_ADVANCE * mults['advance']
        if landing is None:
            return -9999
        score += dice_roll * _W_ADVANCE * mults['advance']
        score += _W_SAFE_BONUS * mults['safe']
        return score
 
    landing = simulate_move(pawn, dice_roll, path_cells, final_paths)
    if landing is None:
        return -9999
 
    lands_in_final = getattr(landing, 'is_final', False)
 
    # Fattore: mangia un nemico
    for enemy in all_pawns:
        if (enemy.player.index != player.index
                and enemy.current_cell == landing
                and not enemy.current_cell.is_home
                and not getattr(enemy, 'at_goal', False)):
            enemy_adv = max(position_score(enemy), 0)
            score += (_W_EAT_BASE + enemy_adv) * mults['eat']
            break
 
    # Fattore: entra nel percorso finale
    if lands_in_final and not getattr(pawn.current_cell, 'is_final', False):
        score += _W_ENTER_FINAL * mults['enter']
 
    # Fattore: già nel finale (bonus sicurezza)
    if lands_in_final:
        score += _W_SAFE_BONUS * mults['safe']
 
    # Fattore: avanzamento
    if not lands_in_final:
        score += dice_roll * _W_ADVANCE * mults['advance']
    else:
        score += dice_roll * _W_ADVANCE * 0.5 * mults['advance']
 
    # Fattore: pericolo della destinazione
    if not lands_in_final:
        danger = cell_danger(landing, player.index, all_pawns, path_cells, final_paths)
        score += danger * _W_DANGER * mults['danger']
 
    # Fattore: predict rilancio dado=6
    if dice_roll == 6:
        reroll_val = _expected_reroll_value(player, players, path_cells, final_paths)
        score += reroll_val * (_W_PREDICT_6 / 100.0) * mults['predict']
 
    return score


def ai_strategist(player, players, dice_roll, path_cells, final_paths):
    """
    AI adattiva con valutazione euristica multi-fattore.
    Sceglie la mossa con il punteggio più alto.
    """
    valid = get_valid_pawns(player, players, dice_roll, path_cells, final_paths)
    if not valid:
        return None
 
    all_pawns = all_pawns_list(players)
    phase = _game_phase(player, players)
    mults = _phase_weights(phase)
 
    best_pawn = None
    best_score = float('-inf')
 
    for pawn in valid:
        s = _score_move(pawn, dice_roll, player, players, path_cells, final_paths,
                        all_pawns, phase, mults)
        if s > best_score:
            best_score = s
            best_pawn = pawn
 
    return best_pawn or random.choice(valid)


# =============================================================================
# ENTRY POINT
# =============================================================================

_AI_MAP = {
    'Scimmia':   ai_monkey,
    'Lepre':     ai_hare,
    'Tartaruga': ai_turtle,
    'Leone':     ai_lion,
    'Stratega':  ai_strategist,
}


def bot_choose_move(player, players, dice_roll, path_cells, final_paths):
    """
    Entry point principale: restituisce la Pedina scelta dal bot.
    """
    level = getattr(player, 'ai_level', 'Stratega')
    ai_fn = _AI_MAP.get(level, ai_strategist)
    return ai_fn(player, players, dice_roll, path_cells, final_paths)
