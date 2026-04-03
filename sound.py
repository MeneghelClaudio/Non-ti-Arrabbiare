"""
sound.py - Gestione audio del gioco
===================================

Struttura file audio:
  assets/sounds/ → click.wav, dice.wav, step.wav, leave_home.wav,
                   results.wav, destination.wav, pass.wav, turn.wav,
                   roll_6.wav, eat.wav
  assets/music/  → *.mp3 (shufflati in playlist automatica)

Nota: modifica _SOUNDS_DIR e _MUSIC_DIR per cambiare i percorsi.
      modifica VOLUME_SFX e VOLUME_MUSIC per cambiare i volumi.
"""

import os
import random
import pygame
import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    base = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(os.path.join(base, "assets")):
        return base
    return os.path.dirname(base)

_BASE_DIR = get_base_path()
_SOUNDS_DIR = os.path.join(_BASE_DIR, "assets", "sounds")
_MUSIC_DIR = os.path.join(_BASE_DIR, "assets", "music")

# Volume (0.0 – 1.0)
VOLUME_SFX = 1.0
VOLUME_MUSIC = 0.5

# Mappa nome logico → file
_SFX_FILES = {
    "click":       "click.wav",
    "dice":        "dice.wav",
    "step":        "step.wav",
    "leave_home":  "leave_home.wav",
    "results":     "results.wav",
    "destination": "destination.wav",
    "pass":        "pass.wav",
    "turn":        "turn.wav",
    "roll_6":      "roll_6.wav",
    "eat":         "eat.wav",
}


class SoundManager:
    """
    Gestisce tutti gli effetti sonori e la musica di sottofondo.
    Implementa singleton tramite _global_sfx.
    """
    
    def __init__(self):
        self._ready = False
        self._muted = False
        self._muted_sfx = False
        self._muted_music = False
        self._sounds = {}
        self._playlist = []
        self._pl_index = 0

        self._init_mixer()
        self._load_sfx()
        self._build_playlist()
        self._start_music()

        try:
            import pedine as _pm
            _pm._sfx_instance = self
        except Exception:
            pass

    # =========================================================================
    # INIZIALIZZAZIONE
    # =========================================================================

    def _init_mixer(self):
        """Inizializza il mixer audio."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._ready = True
        except Exception as e:
            print(f"[SoundManager] mixer non disponibile: {e}")

    def _load_sfx(self):
        """Carica tutti gli effetti sonori in memoria."""
        if not self._ready:
            return
        for name, filename in _SFX_FILES.items():
            path = os.path.join(_SOUNDS_DIR, filename)
            if os.path.isfile(path):
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(VOLUME_SFX)
                    self._sounds[name] = snd
                except Exception as e:
                    print(f"[SoundManager] errore caricamento '{path}': {e}")

    def _build_playlist(self):
        """Costruisce la playlist dalla cartella musica."""
        if not self._ready:
            return
        if not os.path.isdir(_MUSIC_DIR):
            return
        exts = {".mp3", ".ogg", ".wav"}
        tracks = [
            os.path.join(_MUSIC_DIR, f)
            for f in os.listdir(_MUSIC_DIR)
            if os.path.splitext(f)[1].lower() in exts
        ]
        if not tracks:
            return
        random.shuffle(tracks)
        self._playlist = tracks
        self._pl_index = 0

    def _start_music(self):
        """Avvia la riproduzione della musica."""
        if not self._ready or not self._playlist:
            return
        muted = self._muted or self._muted_music
        try:
            pygame.mixer.music.set_volume(0.0 if muted else VOLUME_MUSIC)
            pygame.mixer.music.load(self._playlist[self._pl_index])
            pygame.mixer.music.play()
        except Exception as e:
            print(f"[SoundManager] errore avvio musica: {e}")

    # =========================================================================
    # API PUBBLICA
    # =========================================================================

    def play(self, name: str):
        """Riproduce un effetto sonoro per nome logico."""
        if not self._ready or self._muted or self._muted_sfx:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.play()

    def set_muted(self, muted: bool):
        """Muta/smuta tutto l'audio (SFX + musica)."""
        self._muted = muted
        if not self._ready:
            return
        effective_music = muted or self._muted_music
        pygame.mixer.music.set_volume(0.0 if effective_music else VOLUME_MUSIC)
        if not muted and not pygame.mixer.music.get_busy():
            self._start_music()

    def set_muted_sfx(self, muted: bool):
        """Muta/smuta solo gli effetti sonori."""
        self._muted_sfx = muted

    def set_muted_music(self, muted: bool):
        """Muta/smuta solo la musica di sottofondo."""
        self._muted_music = muted
        if not self._ready:
            return
        effective = self._muted or muted
        pygame.mixer.music.set_volume(0.0 if effective else VOLUME_MUSIC)
        if not effective and not pygame.mixer.music.get_busy():
            self._start_music()

    def is_muted(self) -> bool:
        """True se l'audio globale è mutato."""
        return self._muted

    def update(self):
        """
        Da chiamare ogni frame: gestisce l'avanzamento della playlist.
        """
        if not self._ready or not self._playlist:
            return
        if self._muted or self._muted_music:
            return
        if not pygame.mixer.music.get_busy():
            self._pl_index += 1
            if self._pl_index >= len(self._playlist):
                random.shuffle(self._playlist)
                self._pl_index = 0
            try:
                pygame.mixer.music.load(self._playlist[self._pl_index])
                pygame.mixer.music.set_volume(VOLUME_MUSIC)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"[SoundManager] errore avanzamento playlist: {e}")


# Istanza globale per start_screen/end_screen (tkinter)
_global_sfx = None


def play_click():
    """Click standalone per start_screen and end_screen."""
    # Always use fallback - the global sfx may have closed mixer after game ends
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.init()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        path = os.path.join(_SOUNDS_DIR, "click.wav")
        if os.path.isfile(path):
            pygame.mixer.Sound(path).play()
    except Exception:
        pass
