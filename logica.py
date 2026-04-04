"""
logica.py - Logica di validazione e simulazione delle mosse
==========================================================

Questo modulo contiene le funzioni per:
  - Simulare il movimento di una pedina
  - Validare se una pedina può essere mossa
  - Calcolare lo slot obiettivo nel percorso finale
"""

from pedine import compute_goal_cell


def get_goal_slot(pedina, final_path):
    """
    Restituisce la cella-slot assegnata (o da assegnare) a una pedina
    nel percorso finale.
    
    Args:
        pedina: la Pedina
        final_path: lista delle celle finali per il giocatore
        
    Returns:
        La Cella goal assegnata, o None
    """
    return compute_goal_cell(pedina)


def simulate_move(pedina, steps, path_cells, final_paths):
    """
    Simula lo spostamento di 'steps' passi a partire dalla posizione corrente.
    
    La simulazione gestisce i casi speciali:
      - La cella is_end viene attraversata normalmente
      - Quando la pedina SI TROVA su is_end, il passo successivo entra in final_path[0]
      - Se supera il proprio slot goal, restituisce None (mossa impossibile)
    
    Args:
        pedina: la Pedina da simulare
        steps: numero di passi da fare
        path_cells: lista delle celle del percorso principale
        final_paths: dict {player_index: [celle_finali]}
        
    Returns:
        La Cella di destinazione finale, oppure None se la mossa è impossibile
    """
    fp = final_paths.get(pedina.player.index, [])
    cell = pedina.current_cell
    remaining = steps
    goal_slot = get_goal_slot(pedina, fp)
    goal_slot_idx = fp.index(goal_slot) if (goal_slot and fp) else (len(fp) - 1 if fp else 0)

    while remaining > 0:
        # Caso 1: già dentro il percorso finale
        if cell.is_final and cell in fp:
            idx = fp.index(cell)
            dest_idx = idx + remaining
            if dest_idx > goal_slot_idx:
                return None  # Sfora oltre lo slot assegnato
            return fp[dest_idx]

        # Caso 2: sulla cella is_end del proprio giocatore
        if (getattr(cell, 'is_end', False) and
                getattr(cell, 'player', None) == pedina.player.index and fp):
            remaining -= 1
            if remaining == 0:
                return fp[0]
            dest_idx = remaining
            if dest_idx > goal_slot_idx:
                return None
            return fp[dest_idx]

        # Caso 3: percorso principale - avanza di un passo
        curr_idx = path_cells.index(cell)
        next_idx = (curr_idx + 1) % len(path_cells)
        cell = path_cells[next_idx]
        remaining -= 1

    return cell


def is_pawn_valid(pedina, players, current_player_index, dice_roll, path_cells, final_paths):
    """
    Controlla se una pedina può essere mossa con il dado corrente.
    
    Args:
        pedina: la Pedina da controllare
        players: lista di tutti i Player
        current_player_index: indice del giocatore corrente
        dice_roll: valore del dado
        path_cells: lista delle celle del percorso principale
        final_paths: dict {player_index: [celle_finali]}
        
    Returns:
        True se la pedina può essere mossa
    """
    # Non è il giocatore proprietario
    if pedina.player.index != current_player_index:
        return False

    # Caso 1: pedina in casa - può uscire solo con 6
    if pedina.current_cell.is_home:
        if dice_roll != 6:
            return False
        # Verifica che la cella di partenza non sia occupata da una pedina amica
        from celle import get_start_for_player
        start_cell = get_start_for_player(current_player_index, path_cells)
        if start_cell is None:
            return True
        for player in players:
            for p in player.pedine:
                if p != pedina and p.current_cell == start_cell and p.player.index == current_player_index:
                    return False
        return True

    # Caso 2: pedina già al traguardo - non si muove più
    if getattr(pedina, 'at_goal', False):
        return False

    # Caso 3: calcola la destinazione
    target_cell = simulate_move(pedina, dice_roll, path_cells, final_paths)
    if target_cell is None:
        return False  # Mossa impossibile

    # Caso 4: la destinazione non deve essere occupata da una pedina amica
    # Le pedine nel percorso finale hanno slot unici quindi non si sovrappongono mai
    for player in players:
        for p in player.pedine:
            if (p != pedina
                    and p.current_cell == target_cell
                    and p.player.index == current_player_index):
                return False

    return True
