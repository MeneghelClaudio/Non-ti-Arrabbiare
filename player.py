"""
player.py - Classe Player e gestione dei giocatori
==================================================

Un Player rappresenta un giocatore nel gioco (umano o bot).
Contiene le sue pedine e tiene traccia dello stato del turno.
"""

from celle import get_start_for_player, get_end_for_player
from pedine import Pedina
from costanti import *


class Player:
    """
    Rappresenta un giocatore nel gioco.
    
    Attributi:
        index: identificatore univoco del giocatore (0-based)
        pedine: lista delle pedine possedute dal giocatore
        has_won: True se il giocatore ha vinto
        turns: numero di turni giocati
        is_bot: True se controllato dall'intelligenza artificiale
        ai_level: livello AI ('Scimmia', 'Lepre', 'Tartaruga', 'Leone', 'Stratega')
        extra_turn_earned: True se il giocatore ha mangiato e ha diritto a un turno bonus
    """
    
    def __init__(self, index, timers, pedine_per_player):
        self.index = index
        self.pedine = [Pedina(self, timers) for _ in range(pedine_per_player)]
        self.extra_turn_earned = False
        self.has_won = False
        self.turns = 0
        self.is_bot = False
        self.ai_level = 'Casuale'

    def __iter__(self):
        return iter(self.pedine)

    def __getitem__(self, idx):
        return self.pedine[idx]

    def count_pedine_in_home(self):
        """Conta le pedine ancora nella casa del giocatore."""
        return sum(1 for p in self.pedine if p.current_cell.is_home)

    def count_pedine_at_goal(self):
        """Conta le pedine che hanno raggiunto il traguardo (ultima cella finale)."""
        return sum(1 for p in self.pedine if getattr(p, 'at_goal', False))

    def count_pedine_in_final(self):
        """Conta le pedine nel percorso finale (non necessariamente al traguardo)."""
        return sum(1 for p in self.pedine if p.current_cell.is_final)

    def check_victory(self):
        """
        Verifica se il giocatore ha vinto.
        Un giocatore vince quando tutte le sue pedine sono al traguardo.
        
        Returns:
            True se il giocatore ha vinto
        """
        if self.has_won:
            return True
        if len(self.pedine) > 0 and self.count_pedine_at_goal() == len(self.pedine):
            self.has_won = True
            return True
        return False

    def ranking_score(self):
        """
        Calcola un punteggio per la classifica.
        
        Criteri (in ordine di priorità):
          1. Numero di pedine al traguardo (peso maggiore)
          2. Somma degli steps_total di tutte le pedine in movimento
        
        Le pedine in casa contano 0 steps.
        
        Returns:
            Tupla (pedine_al_traguardo, somma_steps) - confrontabile per ordinamento
        """
        pedine_goal = self.count_pedine_at_goal()
        total_steps = sum(
            getattr(p, 'steps_total', 0)
            for p in self.pedine
            if not p.current_cell.is_home
        )
        return (pedine_goal, total_steps)
