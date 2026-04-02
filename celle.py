"""
celle.py - Definizione della classe Cella e helper per il tabellone
====================================================================

Una Cella rappresenta una posizione sul tabellone di gioco.
Le celle possono essere di diversi tipi:
  - path: celle del percorso principale
  - home: celle slot all'interno delle case dei giocatori
  - final: celle del percorso finale (traguardo)
"""

from costanti import BLACK
from draw import draw_circle


class Cella:
    """
    Rappresenta una singola cella sul tabellone.
    
    Attributi:
        x, y: coordinate pixel della cella
        tipo: 'path', 'home', o 'final'
        index: indice all'interno del tipo di cella
        is_start: True se è la cella di partenza di un giocatore
        is_end: True se è la cella di ingresso al percorso finale
        is_intersection: True se è una cella di incrocio tra bracci
        is_home: True se è una cella slot della casa
        is_final: True se è nel percorso finale (traguardo)
        player: indice del giocatore proprietario (per home, start, end, final)
    """
    
    def __init__(self, x, y, tipo, index=None,
                 is_start=False, is_end=False, is_intersection=False, 
                 is_home=False, player=None, is_final=False):
        self.x = x
        self.y = y
        self.tipo = tipo
        self.index = index
        self.is_start = is_start
        self.is_end = is_end
        self.is_intersection = is_intersection
        self.is_home = is_home
        self.player = player
        self.is_final = is_final

    def draw(self, screen, color, radius, border_width=2):
        """Disegna la cella sullo schermo."""
        draw_circle(screen, (int(self.x), int(self.y)), radius, color, BLACK, border_width)

    def get_pedine_in_cell(self, all_pedine):
        """
        Restituisce la lista delle pedine che si trovano in questa cella.
        
        Args:
            all_pedine: lista flat di tutti gli oggetti Pedina nel gioco
            
        Returns:
            Lista di Pedina presenti in questa cella
        """
        pedine_nella_cella = []
        for pedina in all_pedine:
            if pedina.current_cell == self:
                pedine_nella_cella.append(pedina)
        return pedine_nella_cella


def get_start_for_player(player_index, path_cells):
    """
    Trova la cella di partenza (is_start) per un giocatore specifico.
    
    Args:
        player_index: indice del giocatore (0-based)
        path_cells: lista delle celle del percorso principale
        
    Returns:
        La Cella di start per il giocatore, o None se non trovata
    """
    for cell in path_cells:
        if cell.is_start and cell.player == player_index:
            return cell
    return None


def get_end_for_player(player_index, path_cells):
    """
    Trova la cella di fine (is_end) per un giocatore specifico.
    La cella is_end è dove il giocatore entra nel percorso finale.
    
    Args:
        player_index: indice del giocatore (0-based)
        path_cells: lista delle celle del percorso principale
        
    Returns:
        La Cella is_end per il giocatore, o None se non trovata
    """
    for cell in path_cells:
        if cell.is_end and cell.player == player_index:
            return cell
    return None
