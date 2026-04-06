import tkinter as tk
from tkinter import messagebox
import json, os, sys, subprocess

def _play_click():
    try:
        import pygame
        if not pygame.get_init():
            pygame.init()
        # Gestione del sound manager per evitare errori di riproduzione dei suoni
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "assets", "sounds", "click.wav")
        if os.path.isfile(path):
            pygame.mixer.Sound(path).play()
    except Exception:
        pass

def _play_results():
    try:
        import pygame
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "assets", "sounds", "results.wav")
        if os.path.isfile(path):
            pygame.mixer.Sound(path).play()
    except Exception:
        pass

# ── Click interceptor globale ──────────────────────────────────────────────────
def _setup_click_interceptor(root):
    _INTERACTIVE_TYPES = (
        tk.Button, tk.Checkbutton, tk.Radiobutton,
        tk.Menubutton, tk.Entry, tk.Scale,
        tk.Listbox, tk.Spinbox,
    )
    def on_click(event):
        w = event.widget
        while w is not None and w is not root:
            if isinstance(w, _INTERACTIVE_TYPES):
                _play_click()
                break
            w = getattr(w, 'master', None)
    root.bind('<Button-1>', on_click, add='+')

# ── Palette (identica a start_screen) ─────────────────────────────────────────
BG_ROOT    = "#d0d0d8"
BG_PANEL   = "#1e1a2e"
BG_PANEL2  = "#2a2540"
BG_ROW_A   = "#2a2540"
BG_ROW_B   = "#241f38"
BG_HDR     = "#161228"
BORDER_D   = "#0e0b1a"
BORDER_GOLD= "#b8860b"
ACCENT_RED = "#8b2020"
ACCENT_BLUE= "#2980b9"
ACCENT_GRN = "#27ae60"
TEXT_W     = "#e8e0f0"
TEXT_Y     = "#f0d060"
TEXT_M     = "#8880a8"
TEXT_DIM   = "#605880"

MEDALS = ["🥇", "🥈", "🥉"]

# Colori importati da costanti.py
from costanti import PLAYER_COLORS_HEX as PLAYER_COLORS, AI_EMOJI

def darken(h, f=0.7):
    r,g,b = int(h[1:3],16),int(h[3:5],16),int(h[5:7],16)
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

def lighten(h, f=1.2):
    r=min(255,int(int(h[1:3],16)*f))
    g=min(255,int(int(h[3:5],16)*f))
    b=min(255,int(int(h[5:7],16)*f))
    return f"#{r:02x}{g:02x}{b:02x}"

def clamp(v,lo,hi): return max(lo,min(hi,v))


class EndScreen:
    """
    Uso:
        config = json.load(open(sys.argv[1], encoding="utf-8"))
        # Ogni player deve avere anche "pawns_home" e "turns" nel config
        EndScreen(root, config)

    Oppure passando direttamente la lista risultati:
        EndScreen(root, {
            "players": [
                {"name":"Mario","color":"Rosso","hex":"#e63946",
                 "pawns_home":4,"turns":22,"bot":False},
                ...
            ],
            "pawns_each": 4
        })
    """
    def __init__(self, root, game_data: dict):
        self.root = root
        self.root.title("Non t'Arrabbiare - Schermata Finale")
        self.root.configure(bg=BG_ROOT)
        self.root.resizable(True, True)
        self.root.minsize(460, 360)

        # Logo del gioco nella finestra dell'applicazione
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "Non_ti_Arrabbiare_logo.ico")
        if os.path.isfile(logo_path):
            self.root.iconbitmap(logo_path)

        self.scale = 1.0
        self._rebuild_pending = False
        self._last_w = 0

        # Ordinamento (vale sempre, anche per "Termina partita"):
        # 1° criterio: più pedine al traguardo (desc)
        # 2° criterio (parità): pedina più vicina al traguardo → best_steps (desc)
        players = game_data.get("players", [])
        self.pawns_each = game_data.get("pawns_each", 4)
        self.results = sorted(
            players,
            key=lambda p: (
                -p.get("pawns_home", 0),
                -p.get("best_steps", 0),
            )
        )
        self.winner = self.results[0] if self.results else None

        self.root.grid_rowconfigure(0, weight=0)  # titolo fisso
        self.root.grid_rowconfigure(1, weight=1)  # area scrollabile
        self.root.grid_rowconfigure(2, weight=0)  # bottoni fissi
        self.root.grid_columnconfigure(0, weight=1)

        self._vbar_visible = False
        self._setup_scroll()
        self._build_all()
        self._initial_size()
        self.root.bind("<Configure>", self._on_resize)
        _play_results()

        _setup_click_interceptor(self.root)

    # ── Scroll ────────────────────────────────────────────────────────────────
    def _setup_scroll(self):
        sf = tk.Frame(self.root, bg=BG_ROOT)
        sf.grid(row=1, column=0, sticky="nsew")
        sf.grid_rowconfigure(0, weight=1)
        sf.grid_columnconfigure(0, weight=1)

        self.vbar = tk.Scrollbar(sf, orient="vertical",
                                 troughcolor=BG_PANEL, bg=BG_PANEL2)
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.vbar.grid_remove()

        self.canvas = tk.Canvas(sf, bg=BG_ROOT, highlightthickness=0,
                                yscrollcommand=self._yscroll_cb)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.config(command=self.canvas.yview)

        self.inner = tk.Frame(self.canvas, bg=BG_ROOT)
        self._win_id = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>",  self._on_inner_conf)
        self.canvas.bind("<Configure>", self._on_canvas_conf)
        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))

    def _yscroll_cb(self, first, last):
        need = not (float(first) <= 0.0 and float(last) >= 1.0)
        if need != self._vbar_visible:
            self._vbar_visible = need
            if need:
                self.vbar.grid()
            else:
                self.vbar.grid_remove()
        self.vbar.set(first, last)

    def _on_inner_conf(self, e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_conf(self, e=None):
        self.canvas.itemconfig(self._win_id, width=self.canvas.winfo_width())

    # ── Scale ─────────────────────────────────────────────────────────────────
    def _recompute_scale(self):
        self.root.update_idletasks()
        w = max(self.root.winfo_width() - 20, 1)
        self.scale = clamp(w / 560, 0.5, 2.2)

    def _s(self, v):  return max(1, int(round(v * self.scale)))
    def _fs(self, v): return clamp(int(round(v * self.scale)), max(6,v-3), v+10)
    def _rh(self):    return max(22, int(32 * self.scale))

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_all(self):
        self._recompute_scale()
        # Distruggi solo titolo (riga 0) e bottoni (riga 2); lo scroll (riga 1) è fisso
        for w in self.root.grid_slaves(row=0):
            w.destroy()
        for w in self.root.grid_slaves(row=2):
            w.destroy()
        # Svuota l'inner scrollabile
        for w in self.inner.winfo_children():
            w.destroy()

        s = self._s; fs = self._fs; rh = self._rh()

        # ── Titolo (riga 0, fisso) ─────────────────────────────────────────────
        title_outer = tk.Frame(self.root, bg=BG_ROOT)
        title_outer.grid(row=0, column=0, sticky="ew", padx=s(20), pady=(s(16), s(8)))

        title_border = tk.Frame(title_outer, bg=BORDER_GOLD, padx=2, pady=2)
        title_border.pack(fill="x")

        title_panel = tk.Frame(title_border, bg=BG_PANEL, padx=s(20), pady=s(10))
        title_panel.pack(fill="x")

        tk.Label(title_panel, text="PARTITA FINITA",
                 font=("Impact", fs(22)), fg=TEXT_Y,
                 bg=BG_PANEL).pack()

        # Vincitore
        if self.winner:
            w_hex  = self.winner.get("hex", "#888")
            w_name = self.winner.get("name", "?")
            winner_frame = tk.Frame(title_panel, bg=BG_PANEL)
            winner_frame.pack(pady=(s(4), 0))

            dot = max(12, int(rh * 0.55))
            cv  = tk.Canvas(winner_frame, width=dot, height=dot,
                            bg=BG_PANEL, highlightthickness=0)
            cv.pack(side="left", padx=(0, s(6)))
            r2 = max(1, dot//2 - 1)
            cx = cy = dot//2
            cv.create_oval(cx-r2, cy-r2, cx+r2, cy+r2,
                            fill=w_hex, outline="#ffffff", width=1)
            tk.Label(winner_frame,
                     text=f"Ha vinto  {w_name}!",
                     font=("Segoe UI", fs(12), "bold"),
                     fg=TEXT_W, bg=BG_PANEL).pack(side="left")

        tk.Frame(title_outer, height=2, bg=BORDER_GOLD).pack(fill="x", pady=(s(8), 0))

        # ── Tabella risultati (dentro inner scrollabile, riga 1) ──────────────
        wrap = tk.Frame(self.inner, bg=BG_ROOT)
        wrap.pack(fill="x", padx=s(20), pady=(s(8), s(8)))

        tbl_border = tk.Frame(wrap, bg=BORDER_GOLD, padx=1, pady=1)
        tbl_border.pack(fill="x")

        tbl_outer = tk.Frame(tbl_border, bg=BG_PANEL)
        tbl_outer.pack(fill="x")

        tbl = tk.Frame(tbl_outer, bg=BG_PANEL)
        tbl.pack(fill="x", padx=s(6), pady=s(6))

        col_w = [8, 42, 25, 25]
        for ci, w in enumerate(col_w):
            tbl.grid_columnconfigure(ci, weight=w, uniform="tcols")

        # Header
        hdr = tk.Frame(tbl, bg=BG_HDR)
        hdr.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, s(3)))
        for ci, (txt, anchor) in enumerate([
            ("#",        "center"),
            ("GIOCATORE","w"),
            ("🏠",       "center"),
            ("🎯",       "center"),
        ]):
            tk.Label(hdr, text=txt,
                     font=("Impact", fs(9)), fg=TEXT_Y,
                     bg=BG_HDR, anchor=anchor,
                     padx=s(4)
                     ).grid(row=0, column=ci, sticky="ew", ipady=s(3))
        hdr.grid_columnconfigure(0, weight=col_w[0], uniform="hcols")
        hdr.grid_columnconfigure(1, weight=col_w[1], uniform="hcols")
        hdr.grid_columnconfigure(2, weight=col_w[2], uniform="hcols")
        hdr.grid_columnconfigure(3, weight=col_w[3], uniform="hcols")

        # Sotto-header
        sub = tk.Frame(tbl, bg=BG_PANEL2)
        sub.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, s(4)))
        sub.grid_columnconfigure(0, weight=col_w[0], uniform="scols")
        sub.grid_columnconfigure(1, weight=col_w[1], uniform="scols")
        sub.grid_columnconfigure(2, weight=col_w[2], uniform="scols")
        sub.grid_columnconfigure(3, weight=col_w[3], uniform="scols")
        tk.Label(sub, text="", bg=BG_PANEL2).grid(row=0, column=0, sticky="ew")
        tk.Label(sub, text="", bg=BG_PANEL2).grid(row=0, column=1, sticky="ew")
        tk.Label(sub, text="al traguardo",
                 font=("Segoe UI", fs(7)), fg=TEXT_M,
                 bg=BG_PANEL2, anchor="center"
                 ).grid(row=0, column=2, sticky="ew", ipady=s(1))
        tk.Label(sub, text="sul tabellone",
                 font=("Segoe UI", fs(7)), fg=TEXT_M,
                 bg=BG_PANEL2, anchor="center"
                 ).grid(row=0, column=3, sticky="ew", ipady=s(1))

        for idx, p in enumerate(self.results):
            tbl.grid_rowconfigure(idx + 2, minsize=rh)
            self._result_row(tbl, p, idx, row_i=idx+2)

        # ── Bottoni (riga 2, fissi) ────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=BG_PANEL)
        btn_frame.grid(row=2, column=0, sticky="ew")

        # Bordo oro sopra
        tk.Frame(btn_frame, height=2, bg=BORDER_GOLD
                 ).pack(fill="x", side="top")

        inner_btn = tk.Frame(btn_frame, bg=BG_PANEL,
                             padx=s(16), pady=s(4))
        inner_btn.pack(fill="x")
        inner_btn.grid_columnconfigure(0, weight=1)
        inner_btn.grid_columnconfigure(1, weight=0)
        inner_btn.grid_columnconfigure(2, weight=1)

        # Logo al centro
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "Non_ti_Arrabbiare_logo.png")
        if os.path.isfile(logo_path):
            try:
                from PIL import Image, ImageTk
                logo_img = Image.open(logo_path)
                w_img, h_img = logo_img.size
                max_h = s(70) # dimensione del logo
                if h_img > max_h:
                    scale = max_h / h_img
                    logo_img = logo_img.resize((int(w_img * scale), int(h_img * scale)), Image.LANCZOS)
                logo_tk = ImageTk.PhotoImage(logo_img)
                logo_label = tk.Label(inner_btn, image=logo_tk, bg=BG_PANEL)
                logo_label.image = logo_tk
                logo_label.grid(row=0, column=1, padx=s(10))
            except Exception:
                pass

        self._mk_btn(inner_btn, "🔄  NUOVA PARTITA",
                     self._new_game, ACCENT_BLUE, 0, "w")
        self._mk_btn(inner_btn, "✖  ESCI",
                     self._exit, ACCENT_RED, 2, "e")

    def _result_row(self, tbl, p, idx, row_i):
        s = self._s; fs = self._fs; rh = self._rh()
        bg_row    = BG_ROW_A if row_i % 2 == 0 else BG_ROW_B
        is_winner = (idx == 0)

        # Colori podio: oro, argento, bronzo
        PODIUM_BG  = ["#3a2a10", "#252830", "#2a1e14"]
        PODIUM_FG  = ["#f0d060", "#c0c8d0", "#c8956a"]
        if idx < 3:
            bg_row   = PODIUM_BG[idx]
            fg_podio = PODIUM_FG[idx]
        else:
            fg_podio = TEXT_DIM

        hex_c         = p.get("hex", "#888")
        pawns_home    = p.get("pawns_home", 0)
        pawns_on_board = p.get("pawns_on_board", 0)
        pos_txt       = MEDALS[idx] if idx < 3 else f"{idx+1}°"

        # Contenitore riga: usa pack per garantire altezza minima
        row = tk.Frame(tbl, bg=bg_row, height=rh)
        row.grid(row=row_i, column=0, columnspan=4, sticky="ew", pady=s(1))
        row.pack_propagate(False)
        row.grid_propagate(False)
        row.grid_columnconfigure(0, weight=8,  uniform="rw")
        row.grid_columnconfigure(1, weight=42, uniform="rw")
        row.grid_columnconfigure(2, weight=25, uniform="rw")
        row.grid_columnconfigure(3, weight=25, uniform="rw")

        # ── Colonna 0: posizione + bordo sinistro colorato ────────────────────
        pos_cell = tk.Frame(row, bg=bg_row)
        pos_cell.grid(row=0, column=0, sticky="nsew")
        # Bordo sinistro colorato (frame stretto)
        tk.Frame(pos_cell, width=s(4), bg=hex_c).pack(side="left", fill="y")
        tk.Label(pos_cell, text=pos_txt,
                 font=("Impact", fs(10)),
                 fg=fg_podio,
                 bg=bg_row
                 ).pack(side="left", padx=s(4), fill="both", expand=True)

        # ── Colonna 1: pallino + nome ─────────────────────────────────────────
        name_cell = tk.Frame(row, bg=bg_row)
        name_cell.grid(row=0, column=1, sticky="nsew")

        dot = max(10, int(rh * 0.48))
        cv  = tk.Canvas(name_cell, width=dot, height=dot,
                        bg=bg_row, highlightthickness=0)
        cv.pack(side="left", padx=(s(4), s(3)), pady=s(2))
        r2 = max(1, dot // 2 - 1)
        cx = cy = dot // 2
        cv.create_oval(cx - r2, cy - r2, cx + r2, cy + r2,
                       fill=hex_c, outline="#ffffff", width=1)

        tk.Label(name_cell, text=p.get("name", "?"),
                 font=("Segoe UI", fs(9), "bold"),
                 fg=fg_podio,
                 bg=bg_row, anchor="w"
                 ).pack(side="left", fill="both", expand=True)

        if p.get("bot", False):
            ai_level = p.get("ai_level", "")
            emoji = AI_EMOJI.get(ai_level, '(🤖)')
            tk.Label(name_cell, text=f" {emoji}",
                     font=("Segoe UI", fs(9)),
                     fg=fg_podio,
                     bg=bg_row, anchor="w"
                     ).pack(side="left", fill="both", expand=True)

        # ── Colonna 2: pedine al traguardo (canvas con cerchi uguali) ──────────
        home_cell = tk.Frame(row, bg=bg_row)
        home_cell.grid(row=0, column=2, sticky="nsew")
        self._pawn_icons_canvas(home_cell, pawns_home, self.pawns_each, hex_c, bg_row, rh, s)

        # ── Colonna 3: pedine sul tabellone ──────────────────────────────────
        board_cell = tk.Frame(row, bg=bg_row)
        board_cell.grid(row=0, column=3, sticky="nsew")
        board_txt = str(pawns_on_board) if pawns_on_board > 0 else "–"
        tk.Label(board_cell, text=board_txt,
                 font=("Impact", fs(11)),
                 fg=fg_podio if (idx < 3 and pawns_on_board > 0) else TEXT_W,
                 bg=bg_row, anchor="center"
                 ).pack(fill="both", expand=True, padx=s(2))

    def _pawn_icons(self, home, total, hex_c):
        """Mantenuto per compatibilità — non usato."""
        filled = min(home, total)
        empty  = total - filled
        return "●" * filled + "○" * empty

    def _pawn_icons_canvas(self, parent, home, total, hex_c, bg, rh, s):
        """Disegna le pedine come cerchi canvas — filled e empty della stessa dimensione."""
        import tkinter as tk
        n = max(total, 1)
        dot_r = max(4, int(rh * 0.22))   # raggio cerchio
        gap   = max(2, int(rh * 0.08))
        total_w = n * (dot_r * 2) + (n - 1) * gap
        cv_h  = rh
        cv = tk.Canvas(parent, bg=bg, highlightthickness=0,
                       width=total_w, height=cv_h)
        cv.pack(expand=True)
        y = cv_h // 2
        for i in range(n):
            x = dot_r + i * (dot_r * 2 + gap)
            if i < home:
                # Piena — colore player
                cv.create_oval(x - dot_r, y - dot_r, x + dot_r, y + dot_r,
                               fill=hex_c, outline="#ffffff", width=1)
            else:
                # Vuota — solo bordo
                cv.create_oval(x - dot_r, y - dot_r, x + dot_r, y + dot_r,
                               fill=bg, outline="#888888", width=1)

    def _mk_btn(self, parent, text, cmd, bg, col, anchor):
        f = tk.Frame(parent, bg=bg)
        f.grid(row=0, column=col, sticky=anchor)
        def _cmd_with_click(c=cmd): c()
        b = tk.Button(f, text=text, command=_cmd_with_click,
                      bg=bg, fg=TEXT_W,
                      activebackground=darken(bg),
                      activeforeground=TEXT_W,
                      font=("Impact", self._fs(11)),
                      relief="flat", bd=0,
                      padx=self._s(16), pady=self._s(7),
                      cursor="hand2")
        b.pack()
        tk.Frame(f, height=3, bg=darken(bg)).pack(fill="x")
        b.bind("<Enter>", lambda e: b.config(bg=lighten(bg)))
        b.bind("<Leave>", lambda e: b.config(bg=bg))

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _new_game(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        start_path = os.path.join(script_dir, "start_screen.py")
        if os.path.isfile(start_path):
            subprocess.Popen([sys.executable, start_path])
        self.root.destroy()

    def _exit(self):
        self.root.destroy()

    # ── Resize ────────────────────────────────────────────────────────────────
    def _on_resize(self, e=None):
        if e and e.widget is not self.root:
            return
        new_w = self.root.winfo_width()
        if abs(new_w - self._last_w) < 4:
            return
        self._last_w = new_w
        if self._rebuild_pending:
            return
        self._rebuild_pending = True
        self.root.after(100, self._do_rebuild)

    def _do_rebuild(self):
        self._rebuild_pending = False
        self._build_all()

    def _initial_size(self):
        self.root.update_idletasks()
        n   = len(self.results)
        sw  = self.root.winfo_screenwidth()
        sh  = self.root.winfo_screenheight()
        w   = min(560, sw - 80)
        h   = min(320 + n * 36, sh - 80)
        self._last_w = w
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Richiede il file di configurazione come argomento
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
        for i, p in enumerate(data["players"]):
            p.setdefault("pawns_home", [4,2,3,1,0,4,2,1,3][i % 9])
            p.setdefault("turns",      [18,25,22,30,0,16,28,32,20][i % 9])
        root = tk.Tk()
        EndScreen(root, data)
        root.mainloop()
    else:
        print("Usage: python end_screen.py <game_config.json>")
        sys.exit(1)
