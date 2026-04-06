import tkinter as tk
from tkinter import messagebox
import random, json, os, sys, subprocess

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

# ── Palette ────────────────────────────────────────────────────────────────────
BG_ROOT    = "#d0d0d8"
BG_PANEL   = "#1e1a2e"   # pannello scuro principale
BG_PANEL2  = "#2a2540"   # pannello secondario
BG_ROW_A   = "#2a2540"
BG_ROW_B   = "#241f38"
BG_HDR     = "#161228"
BG_TITLE   = "#1e1a2e"
BORDER_D   = "#0e0b1a"
BORDER_L   = "#4a4068"
BORDER_GOLD= "#b8860b"
ACCENT_RED = "#8b1a1a"
ACCENT_BLUE= "#2980b9"
ACCENT_GRN = "#27ae60"
TEXT_W     = "#e8e0f0"
TEXT_Y     = "#f0d060"    # giallo oro titoli
TEXT_M     = "#8880a8"
TEXT_DIM   = "#605880"

# Colori importati da costanti.py
from costanti import PLAYER_COLORS_HEX as PLAYER_COLORS, COLOR_NAMES
BOT_LEVELS  = ["Scimmia", "Lepre", "Tartaruga", "Leone", "Stratega", "Casuale"]
_REAL_LEVELS = [l for l in BOT_LEVELS if l != "Casuale"]

def resolve_level(level: str) -> str:
    """Se il livello è 'Casuale', sceglie casualmente uno dei livelli reali."""
    if level == "Casuale":
        return random.choice(_REAL_LEVELS)
    return level
MAX_TOTAL   = 9
MIN_W, MIN_H = 520, 400
ROW_H_BASE   = 34
SIDE_PAD     = 18


def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def darken(h, f=0.7):
    r,g,b = int(h[1:3],16),int(h[3:5],16),int(h[5:7],16)
    return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

def lighten(h, f=1.2):
    r=min(255,int(int(h[1:3],16)*f))
    g=min(255,int(int(h[3:5],16)*f))
    b=min(255,int(int(h[5:7],16)*f))
    return f"#{r:02x}{g:02x}{b:02x}"


# ── ColorMenuButton ────────────────────────────────────────────────────────────
class ColorMenuButton(tk.Frame):
    def __init__(self, parent, color_var, get_used,
                 bg=BG_ROW_A, font_size=9, row_h=34, **kw):
        super().__init__(parent, bg=bg, height=row_h, **kw)
        self.pack_propagate(False)
        self.color_var = color_var
        self.get_used  = get_used
        self.font_size = font_size
        self.row_h     = row_h
        self._build(bg)

    def _build(self, bg):
        inner = tk.Frame(self, bg=bg)
        inner.place(relx=0, rely=0.5, anchor="w", x=6)

        dot = max(12, int(self.row_h * 0.50))
        self.preview = tk.Canvas(inner, width=dot, height=dot,
                                 bg=bg, highlightthickness=0, cursor="hand2")
        self.preview.pack(side="left", padx=(0, 5))
        self._draw_dot(dot)

        self.mb = tk.Menubutton(inner, textvariable=self.color_var,
                                indicatoron=True, relief="solid",
                                font=("Segoe UI", self.font_size, "bold"),
                                bg=BG_PANEL2, fg="#ffffff",
                                activebackground=BORDER_L,
                                activeforeground="#ffffff",
                                highlightthickness=1,
                                highlightbackground="#000000",
                                cursor="hand2", bd=1)
        self.mb.pack(side="left")

        self.menu = tk.Menu(self.mb, tearoff=False,
                            bg=BG_PANEL, fg=TEXT_W,
                            activebackground=BORDER_L,
                            font=("Segoe UI", self.font_size))
        self.mb["menu"] = self.menu
        self.mb.bind("<ButtonPress>", lambda e: self._populate_menu())
        self._populate_menu()

    def _draw_dot(self, size=None):
        if size is None:
            size = int(self.preview.cget("width"))
        color = PLAYER_COLORS.get(self.color_var.get(), "#ccc")
        self.preview.delete("all")
        r = max(1, size//2 - 1)
        cx = cy = size//2
        # Cerchio pieno senza riflesso
        self.preview.create_oval(cx-r, cy-r, cx+r, cy+r,
                                  fill=color, outline="#ffffff", width=1)

    def _populate_menu(self):
        self.menu.delete(0, "end")
        used    = self.get_used()
        current = self.color_var.get()
        for name in COLOR_NAMES:
            hex_c   = PLAYER_COLORS[name]
            is_used = (name in used and name != current)
            label   = f"  {name}  ✓" if is_used else f"  {name}"
            fg_text = "#000000"
            self.menu.add_command(
                label=label, background=hex_c, foreground=fg_text,
                activebackground=lighten(hex_c),
                font=("Segoe UI", self.font_size, "bold"),
                command=lambda n=name: self._select(n))

    def _select(self, name):
        _play_click()
        self.color_var.set(name)
        self.refresh()

    def refresh(self):
        # Guard: il widget può essere già distrutto durante un rebuild
        try:
            if not self.preview.winfo_exists():
                return
        except Exception:
            return
        self._draw_dot()


# ── StartScreen ────────────────────────────────────────────────────────────────
class StartScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Non t'Arrabbiare - Schermata Iniziale")
        self.root.configure(bg=BG_ROOT)
        self.root.resizable(True, True)
        self.root.minsize(MIN_W, MIN_H)

        # Logo del gioco nella finestra dell'applicazione
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "images", "Non_ti_Arrabbiare_logo.ico")
        if os.path.isfile(logo_path):
            self.root.iconbitmap(logo_path)

        self.scale = 1.0
        self._rebuild_pending = False
        self._last_canvas_w   = 0      # anti-flash: traccia ultima larghezza

        _setup_click_interceptor(self.root)

        self.num_players = tk.IntVar(value=2)
        self.num_pawns   = tk.IntVar(value=4)
        self.num_bots    = tk.IntVar(value=2)
        self.num_players.trace_add("write", self._on_count_change)
        self.num_bots.trace_add("write",    self._on_count_change)

        self._syncing = False   # evita loop tra trace e toggle

        self.p_name        = [tk.StringVar(value=f"Giocatore {i+1}") for i in range(MAX_TOTAL)]
        self.p_name_custom = [False for _ in range(MAX_TOTAL)]
        self.p_color       = [tk.StringVar(value=COLOR_NAMES[i % len(COLOR_NAMES)])
                              for i in range(MAX_TOTAL)]
        self.p_is_bot      = [tk.BooleanVar(value=False) for _ in range(MAX_TOTAL)]
        self.p_level       = [tk.StringVar(value="Casuale") for _ in range(MAX_TOTAL)]

        # Imposta i bot di default e assegna subito i nomi corretti
        _n_p = self.num_players.get()
        _n_b = self.num_bots.get()
        for _i in range(_n_p + _n_b):
            self.p_is_bot[_i].set(_i >= _n_p)
        for _i in range(_n_p + _n_b):
            self._auto_name(_i)

        # Trace su p_is_bot per aggiornamento dinamico
        for _i in range(MAX_TOTAL):
            self.p_is_bot[_i].trace_add("write",
                lambda *_, idx=_i: self._on_bot_toggle(idx))

        self.advanced_visible = False
        self.adv_btn_var = tk.StringVar(value="⚙  Opzioni avanzate")

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        self._setup_scroll()
        self._build_all()
        self._initial_size()
        self.root.bind("<Configure>", self._on_resize)

    # ── Scroll ────────────────────────────────────────────────────────────────
    def _setup_scroll(self):
        sf = tk.Frame(self.root, bg=BG_ROOT)
        sf.grid(row=1, column=0, sticky="nsew")
        sf.grid_rowconfigure(0, weight=1)
        sf.grid_columnconfigure(0, weight=1)

        self.vbar = tk.Scrollbar(sf, orient="vertical",
                                 troughcolor=BG_PANEL, bg=BG_PANEL2)
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.vbar.grid_remove()   # nascosta di default

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

        self._vbar_visible = False

    def _yscroll_cb(self, first, last):
        """Scrollbar callback: mostra/nasconde SENZA triggerare resize."""
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
        # Usa larghezza root invece del canvas per evitare loop scrollbar
        w   = max(self.root.winfo_width() - 20, 1)
        net = max(w - SIDE_PAD * 2, 1)
        base = 820 if self.advanced_visible else 580
        self.scale = clamp(net / base, 0.45, 2.2)

    def _s(self, v):  return max(1, int(round(v * self.scale)))
    def _fs(self, v): return clamp(int(round(v * self.scale)), max(6,v-3), v+10)
    def _rh(self):    return max(24, int(ROW_H_BASE * self.scale))

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_all(self):
        self._recompute_scale()
        for w in self.inner.winfo_children():
            w.destroy()

        s = self._s; fs = self._fs

        # ── Titolo stile "CLASSIFICA" ─────────────────────────────────────────
        outer = tk.Frame(self.inner, bg=BG_ROOT)
        outer.pack(fill="x", padx=s(SIDE_PAD), pady=(s(16), s(8)))

        # Pannello con bordo oro
        title_border = tk.Frame(outer, bg=BORDER_GOLD, padx=2, pady=2)
        title_border.pack(anchor="center")

        title_panel = tk.Frame(title_border, bg=BG_PANEL,
                               padx=s(28), pady=s(10))
        title_panel.pack()

        tk.Label(title_panel, text="NON T'ARRABBIARE",
                 font=("Impact", fs(20)), fg=TEXT_Y,
                 bg=BG_PANEL).pack()
        tk.Label(title_panel, text="Configurazione della partita",
                 font=("Segoe UI", fs(8)), fg=TEXT_M,
                 bg=BG_PANEL).pack()

        # Separatore oro
        tk.Frame(self.inner, height=2, bg=BORDER_GOLD
                 ).pack(fill="x", padx=s(SIDE_PAD), pady=(0, s(10)))

        # ── Corpo ─────────────────────────────────────────────────────────────
        body = tk.Frame(self.inner, bg=BG_ROOT)
        body.pack(fill="both", expand=True,
                  padx=s(SIDE_PAD), pady=(0, s(4)))
        body.grid_columnconfigure(0, weight=30, uniform="body")
        body.grid_columnconfigure(1, weight=0)
        body.grid_columnconfigure(2, weight=70, uniform="body")
        body.grid_rowconfigure(0, weight=1)

        self._build_params(body)
        tk.Frame(body, width=2, bg=BORDER_GOLD
                 ).grid(row=0, column=1, sticky="ns", padx=s(10), pady=s(4))
        self.players_outer = tk.Frame(body, bg=BG_ROOT)
        self.players_outer.grid(row=0, column=2, sticky="nsew")
        self._build_players()

        self._build_bottom()

    def _build_params(self, parent):
        s = self._s; fs = self._fs; rh = self._rh()

        # Bordo oro sottile
        border = tk.Frame(parent, bg=BORDER_GOLD, padx=1, pady=1)
        border.grid(row=0, column=0, sticky="new")

        panel = tk.Frame(border, bg=BG_PANEL,
                         padx=s(16), pady=s(12))
        panel.pack(fill="both")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=0)

        # Header stile classifica
        hdr = tk.Frame(panel, bg=BG_HDR)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew",
                 pady=(0, s(8)), ipady=s(3))
        tk.Label(hdr, text="# PARAMETRI",
                 font=("Impact", fs(10)), fg=TEXT_Y,
                 bg=BG_HDR, anchor="w", padx=s(6)
                 ).pack(fill="x")

        for i, (lbl, var, lo, hi) in enumerate([
            ("Giocatori",  self.num_players, 0, MAX_TOTAL),
            ("Pedine × G", self.num_pawns,   1, 4),
        ], 1):
            panel.grid_rowconfigure(i, minsize=rh)
            row_bg = BG_ROW_A if i % 2 else BG_ROW_B
            row = tk.Frame(panel, bg=row_bg)
            row.grid(row=i, column=0, columnspan=2, sticky="ew",
                     pady=s(1))
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=0)

            # Numero riga stile classifica
            tk.Label(row, text=str(i),
                     font=("Impact", fs(9)), fg=TEXT_DIM,
                     bg=row_bg, width=2
                     ).grid(row=0, column=0, sticky="w", padx=(s(4),0))
            tk.Label(row, text=lbl,
                     font=("Segoe UI", fs(9), "bold"),
                     fg=TEXT_W, bg=row_bg
                     ).grid(row=0, column=0, sticky="w", padx=(s(20),0))
            self._spinner(row, var, lo, hi, bg=row_bg
                          ).grid(row=0, column=1, sticky="e",
                                 padx=(0,s(4)), pady=s(2))

        panel.grid_rowconfigure(3, minsize=rh)
        row_bg = BG_ROW_B if 3 % 2 else BG_ROW_A
        row3 = tk.Frame(panel, bg=row_bg)
        row3.grid(row=3, column=0, columnspan=2, sticky="ew", pady=s(1))
        row3.grid_columnconfigure(0, weight=1)
        row3.grid_columnconfigure(1, weight=0)
        tk.Label(row3, text="3", font=("Impact", fs(9)), fg=TEXT_DIM,
                 bg=row_bg, width=2
                 ).grid(row=0, column=0, sticky="w", padx=(s(4),0))
        tk.Label(row3, text="Bot",
                 font=("Segoe UI", fs(9), "bold"), fg=TEXT_W, bg=row_bg
                 ).grid(row=0, column=0, sticky="w", padx=(s(20),0))
        self.bot_sp = tk.Frame(row3, bg=row_bg)
        self.bot_sp.grid(row=0, column=1, sticky="e", padx=(0,s(4)), pady=s(2))
        self._rebuild_bot_spinner()

    def _rebuild_bot_spinner(self):
        for w in self.bot_sp.winfo_children():
            w.destroy()
        bg = self.bot_sp.cget("bg")
        self._spinner(self.bot_sp, self.num_bots,
                      0, MAX_TOTAL - self.num_players.get(),
                      bg=bg).pack()

    def _build_players(self):
        for w in self.players_outer.winfo_children():
            w.destroy()

        s = self._s; fs = self._fs; rh = self._rh()
        adv   = self.advanced_visible
        n_p   = self.num_players.get()
        n_b   = self.num_bots.get()
        total = n_p + n_b

        # Pannello con bordo oro
        border = tk.Frame(self.players_outer, bg=BORDER_GOLD, padx=1, pady=1)
        border.pack(fill="both", expand=True)

        panel = tk.Frame(border, bg=BG_PANEL)
        panel.pack(fill="both", expand=True)

        g = tk.Frame(panel, bg=BG_PANEL)
        g.pack(fill="both", expand=True, padx=s(4), pady=s(4))

        col_weights = [38, 30] + ([12, 20] if adv else [])
        for ci, w in enumerate(col_weights):
            g.grid_columnconfigure(ci, weight=w, uniform="pcols")

        # Header stile classifica
        hdr_labels = (["#", "GIOCATORE", "COLORE"] +
                      (["BOT", "AI"] if adv else []))

        # Header row unico su tutta la larghezza
        hdr = tk.Frame(g, bg=BG_HDR)
        hdr.grid(row=0, column=0, columnspan=len(col_weights),
                 sticky="ew", pady=(0, s(2)))
        # sottocolonne header
        hdr.grid_columnconfigure(0, weight=4,  uniform="h")
        hdr.grid_columnconfigure(1, weight=col_weights[0], uniform="h")
        hdr.grid_columnconfigure(2, weight=col_weights[1], uniform="h")
        if adv:
            hdr.grid_columnconfigure(3, weight=col_weights[2], uniform="h")
            hdr.grid_columnconfigure(4, weight=col_weights[3], uniform="h")

        for ci, txt in enumerate(hdr_labels):
            tk.Label(hdr, text=txt,
                     font=("Impact", fs(8)), fg=TEXT_Y,
                     bg=BG_HDR, anchor="w", padx=s(4)
                     ).grid(row=0, column=ci, sticky="ew", ipady=s(3))

        for idx in range(total):
            g.grid_rowconfigure(idx + 1, minsize=rh)
            self._player_row(g, idx, row_i=idx+1,
                             is_bot_default=self.p_is_bot[idx].get(), advanced=adv)

        if adv:
            self._build_ai_legend(self.players_outer)

    def _build_ai_legend(self, parent):
        s = self._s; fs = self._fs
        AI_DESCRIPTIONS = [
            ("Scimmia",   "Mosse casuali, mangia sempre se può"),
            ("Lepre",     "Avanza 1 pedina alla volta, mantiene 2+ fuori"),
            ("Tartaruga", "Porta fuori tutte le pedine, avanza compatta"),
            ("Leone",     "Cacciatore: mangia sempre, poi si avvicina al nemico"),
            ("Stratega",  "Valuta ogni mossa con un punteggio multi-fattore e cambia strategia in base alla fase di gioco"),
            ("Casuale",   "Livello scelto casualmente ad ogni partita"),
        ]
        outer = tk.Frame(parent, bg=BORDER_GOLD, padx=1, pady=1)
        outer.pack(fill="x", pady=(s(8), 0))
        panel = tk.Frame(outer, bg=BG_PANEL, padx=s(8), pady=s(6))
        panel.pack(fill="x")
        # Header
        hdr = tk.Frame(panel, bg=BG_HDR)
        hdr.pack(fill="x", pady=(0, s(4)))
        tk.Label(hdr, text="⚙ LEGENDA AI",
                 font=("Impact", fs(9)), fg=TEXT_Y,
                 bg=BG_HDR, anchor="w", padx=s(6)
                 ).pack(fill="x", ipady=s(2))
        # Righe
        for i, (name, desc) in enumerate(AI_DESCRIPTIONS):
            bg = BG_ROW_A if i % 2 == 0 else BG_ROW_B
            row = tk.Frame(panel, bg=bg)
            row.pack(fill="x", pady=s(1))
            tk.Label(row, text=name,
                     font=("Impact", fs(9)), fg=TEXT_Y,
                     bg=bg, width=10, anchor="w", padx=s(6)
                     ).pack(side="left", ipady=s(2))
            tk.Label(row, text=desc,
                     font=("Segoe UI", fs(8)),
                     fg=TEXT_W, bg=bg, anchor="w"
                     ).pack(side="left", fill="x", expand=True, padx=(0, s(6)))

    def _player_row(self, g, idx, row_i, is_bot_default, advanced):
        s = self._s; fs = self._fs; rh = self._rh()
        # Righe alternate come classifica
        bg_row = BG_ROW_A if row_i % 2 else BG_ROW_B
        # Evidenzia riga attiva (giocatore corrente simulato)
        fg_name = "#ff9090" if is_bot_default else TEXT_W
        num_cols = 4 if advanced else 2
        px = s(4)

        def cell(col):
            f = tk.Frame(g, bg=bg_row, relief="flat", bd=0)
            rpad = s(1) if col < num_cols - 1 else 0
            f.grid(row=row_i, column=col,
                   padx=(0, rpad), pady=s(1), sticky="nsew")
            return f

        # ── Numero riga + pallino colore (come classifica) ────────────────────
        nc = cell(0)
        # Bordo sinistro colorato
        player_hex = PLAYER_COLORS.get(self.p_color[idx].get(), "#888")
        tk.Frame(nc, width=s(3), bg=player_hex
                 ).place(x=0, y=0, relheight=1.0)

        num_lbl = tk.Label(nc, text=str(row_i),
                           font=("Impact", fs(10)), fg=TEXT_DIM,
                           bg=bg_row)
        num_lbl.place(x=s(6), rely=0.5, anchor="w")

        def _update_dot(*_):
            try:
                if not nc.winfo_exists():
                    return
            except Exception:
                return
            try:
                h = PLAYER_COLORS.get(self.p_color[idx].get(), "#888")
                if nc.winfo_exists():
                    tk.Frame(nc, width=s(3), bg=h).place(x=0, y=0, relheight=1.0)
            except Exception:
                pass

        # Entry nome
        e = tk.Entry(nc, textvariable=self.p_name[idx],
                     font=("Segoe UI", fs(9), "bold"),
                     bg=bg_row, fg=fg_name,
                     insertbackground=TEXT_W,
                     relief="flat", bd=0)
        e.place(x=s(22), rely=0.5, anchor="w",
                relwidth=1.0, width=-s(26))
        e.bind("<Key>", lambda event, i=idx: self.p_name_custom.__setitem__(i, True))

        # ── COLORE ────────────────────────────────────────────────────────────
        cc = cell(1)
        cmb = ColorMenuButton(
            cc, self.p_color[idx],
            get_used=lambda i=idx: self._used_colors(exclude_idx=i),
            bg=bg_row, font_size=fs(9), row_h=rh)
        self.p_color[idx].trace_add("write",
            lambda *_, c=cmb, u=_update_dot: (c.refresh(), u()))
        cmb.place(relx=0, rely=0.5, anchor="w", relwidth=1.0)

        if not advanced:
            return

        # ── BOT checkbox ──────────────────────────────────────────────────────
        bc = cell(2)
        chk = tk.Checkbutton(bc, variable=self.p_is_bot[idx],
                              bg=bg_row, activebackground=bg_row,
                              selectcolor="#27ae60",
                              fg=TEXT_W, relief="flat",
                              cursor="hand2",
                              command=self._schedule_rebuild)
        chk.place(relx=0.5, rely=0.5, anchor="center")

        # ── AI dropdown ───────────────────────────────────────────────────────
        ac = cell(3)
        enabled = self.p_is_bot[idx].get()
        ai_om = tk.OptionMenu(ac, self.p_level[idx], *BOT_LEVELS)
        ai_om.config(
            bg=BG_PANEL2 if enabled else BG_HDR,
            fg=TEXT_W if enabled else TEXT_M,
            activebackground=BORDER_L, activeforeground=TEXT_W,
            relief="flat", font=("Segoe UI", fs(9), "bold"),
            bd=0, highlightthickness=0,
            state="normal" if enabled else "disabled",
            cursor="hand2")
        ai_om["menu"].config(bg=BG_PANEL, fg=TEXT_W,
                             activebackground=BORDER_L,
                             font=("Segoe UI", fs(9), "bold"))
        ai_om.place(relx=0, rely=0.5, anchor="w",
                    relwidth=1.0, width=-s(2), x=s(1))

    def _build_bottom(self):
        for w in self.root.grid_slaves(row=2):
            w.destroy()

        s = self._s; fs = self._fs

        # Bordo oro sopra
        tk.Frame(self.root, height=2, bg=BORDER_GOLD
                 ).grid(row=2, column=0, sticky="ew")

        bf = tk.Frame(self.root, bg=BG_PANEL,
                      pady=s(4), padx=s(SIDE_PAD))
        bf.grid(row=2, column=0, sticky="ew")
        bf.grid_columnconfigure(0, weight=1)
        bf.grid_columnconfigure(1, weight=0)
        bf.grid_columnconfigure(2, weight=1)

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
                logo_label = tk.Label(bf, image=logo_tk, bg=BG_PANEL)
                logo_label.image = logo_tk
                logo_label.grid(row=0, column=1, padx=s(10))
            except Exception:
                pass

        def mk_btn(parent, text, cmd, bg, col, anchor):
            f = tk.Frame(parent, bg=bg)
            f.grid(row=0, column=col, sticky=anchor)
            def _cmd_with_click(c=cmd): c()
            b = tk.Button(f, text=text, command=_cmd_with_click,
                          bg=bg, fg=TEXT_W,
                          activebackground=darken(bg),
                          activeforeground=TEXT_W,
                          font=("Impact", 13),
                          relief="flat", bd=0,
                          padx=18, pady=8,
                          cursor="hand2")
            b.pack()
            tk.Frame(f, height=3, bg=darken(bg)).pack(fill="x")
            b.bind("<Enter>", lambda e: b.config(bg=lighten(bg)))
            b.bind("<Leave>", lambda e: b.config(bg=bg))

        mk_btn(bf, self.adv_btn_var.get() if not callable(self.adv_btn_var)
               else "⚙  Opzioni avanzate",
               self._toggle_advanced, ACCENT_BLUE, 0, "w")

        # Ricrea il bottone avanzate con textvariable
        for w in bf.grid_slaves(row=0, column=0):
            w.destroy()
        f = tk.Frame(bf, bg=ACCENT_BLUE)
        f.grid(row=0, column=0, sticky="w")
        b = tk.Button(f, textvariable=self.adv_btn_var,
                      command=self._toggle_advanced,
                      bg=ACCENT_BLUE, fg=TEXT_W,
                      activebackground=darken(ACCENT_BLUE),
                      activeforeground=TEXT_W,
                      font=("Impact", 13),
                      relief="flat", bd=0,
                      padx=18, pady=8, cursor="hand2")
        b.pack()
        tk.Frame(f, height=3, bg=darken(ACCENT_BLUE)).pack(fill="x")
        b.bind("<Enter>", lambda e: b.config(bg=lighten(ACCENT_BLUE)))
        b.bind("<Leave>", lambda e: b.config(bg=ACCENT_BLUE))

        mk_btn(bf, "▶  INIZIA LA PARTITA",
               self._start_game, ACCENT_GRN, 2, "e")

    # ── Spinner ───────────────────────────────────────────────────────────────
    def _spinner(self, parent, var, lo, hi, bg=BG_PANEL):
        s = self._s; fs = self._fs
        f = tk.Frame(parent, bg=bg)
        tk.Label(f, textvariable=var, width=3, anchor="center",
                 bg=BG_HDR, fg=TEXT_Y,
                 font=("Impact", fs(12)),
                 relief="flat", bd=0, pady=s(1)
                 ).pack(side="left")
        bf = tk.Frame(f, bg=bg)
        bf.pack(side="left", padx=(2,0))

        def inc():
            if var in (self.num_players, self.num_bots):
                if self.num_players.get() + self.num_bots.get() >= MAX_TOTAL:
                    return
            var.set(min(hi, var.get() + 1))

        def dec():
            var.set(max(lo, var.get() - 1))

        for txt, cmd in [("▲", inc), ("▼", dec)]:
            tk.Button(bf, text=txt, command=cmd,
                      bg=BG_PANEL2, fg=TEXT_Y,
                      relief="flat", font=("Segoe UI", fs(6), "bold"),
                      bd=0, activebackground=BORDER_L,
                      activeforeground=TEXT_W,
                      cursor="hand2").pack(fill="x", pady=1)
        return f

    # ── Colori ────────────────────────────────────────────────────────────────
    def _used_colors(self, exclude_idx=None):
        total = self.num_players.get() + self.num_bots.get()
        return {self.p_color[i].get()
                for i in range(total) if i != exclude_idx}

    def _resolve_duplicates(self):
        total = self.num_players.get() + self.num_bots.get()
        seen  = set()
        for i in range(total):
            c = self.p_color[i].get()
            if c in seen:
                for cand in COLOR_NAMES:
                    if cand not in seen:
                        self.p_color[i].set(cand)
                        seen.add(cand)
                        break
            else:
                seen.add(c)

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_count_change(self, *_):
        if self._syncing:
            return
        try:
            max_b = MAX_TOTAL - self.num_players.get()
            if self.num_bots.get() > max_b:
                self._syncing = True
                self.num_bots.set(max(0, max_b))
                self._syncing = False
        except Exception:
            pass
        # Aggiorna p_is_bot in base ai contatori
        n_p   = self.num_players.get()
        n_b   = self.num_bots.get()
        total = n_p + n_b
        self._syncing = True
        for i in range(total):
            self.p_is_bot[i].set(i >= n_p)
        self._syncing = False
        # Aggiorna nomi non personalizzati
        for i in range(total):
            self._auto_name(i)
        self._resolve_duplicates()
        self._schedule_rebuild()

    def _on_bot_toggle(self, idx):
        """Chiamato quando il checkbox bot cambia: aggiorna contatori e nomi di tutti."""
        if self._syncing:
            return
        total = self.num_players.get() + self.num_bots.get()
        if idx >= total:
            return
        actual_bots    = sum(1 for i in range(total) if self.p_is_bot[i].get())
        actual_players = total - actual_bots
        self._syncing = True
        self.num_players.set(actual_players)
        self.num_bots.set(actual_bots)
        self._syncing = False
        # Ricalcola i nomi di tutti (il cambio di un giocatore sposta la numerazione)
        for i in range(total):
            self._auto_name(i)
        self._schedule_rebuild()

    def _auto_name(self, idx):
        """Assegna nome automatico se non personalizzato."""
        if self.p_name_custom[idx]:
            return
        total = self.num_players.get() + self.num_bots.get()
        if idx >= total:
            return
        is_bot = self.p_is_bot[idx].get()
        if is_bot:
            n = sum(1 for i in range(idx + 1) if self.p_is_bot[i].get())
            self.p_name[idx].set(f"Bot {n}")
        else:
            n = sum(1 for i in range(idx + 1) if not self.p_is_bot[i].get())
            self.p_name[idx].set(f"Giocatore {n}")

    def _schedule_rebuild(self, *_):
        if self._rebuild_pending:
            return
        self._rebuild_pending = True
        self.root.after(10, self._do_rebuild)

    def _do_rebuild(self):
        self._rebuild_pending = False
        self._build_all()

    def _toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        self.adv_btn_var.set("▲ Nascondi avanzate"
                             if self.advanced_visible else "⚙  Opzioni avanzate")
        self._build_all()

    def _on_resize(self, e=None):
        if e and e.widget is not self.root:
            return
        # Anti-flash: ricostruisce solo se la larghezza root cambia davvero
        new_w = self.root.winfo_width()
        if abs(new_w - self._last_canvas_w) < 4:
            return
        self._last_canvas_w = new_w
        if self._rebuild_pending:
            return
        self._rebuild_pending = True
        self.root.after(100, self._do_rebuild)

    def _initial_size(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w  = min(760, sw - 80)
        h  = min(540, sh - 80)
        self._last_canvas_w = w
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Avvio ─────────────────────────────────────────────────────────────────
    def _start_game(self):
        n_p   = self.num_players.get()
        n_b   = self.num_bots.get()
        total = n_p + n_b
        if total < 2:
            messagebox.showwarning("Giocatori insufficienti",
                                   "Servono almeno 2 giocatori o bot per iniziare!")
            return

        colors = [self.p_color[i].get() for i in range(total)]
        if len(colors) != len(set(colors)):
            messagebox.showwarning("Colori duplicati",
                                   "Due o più giocatori hanno lo stesso colore!")
            return

        players = []
        for i in range(total):
            is_bot = self.p_is_bot[i].get() if self.advanced_visible else (i >= n_p)
            players.append({
                "name":  self.p_name[i].get() or f"Slot {i+1}",
                "color": self.p_color[i].get(),
                "hex":   PLAYER_COLORS.get(self.p_color[i].get(), "#888"),
                "bot":   is_bot,
                "level": resolve_level(self.p_level[i].get()) if is_bot else None,
                "pawns": self.num_pawns.get(),
            })

        game_data = {
            "players":     players,
            "num_players": n_p,
            "num_bots":    n_b,
            "pawns_each":  self.num_pawns.get(),
        }

        script_dir  = os.path.dirname(os.path.abspath(__file__))
        ludo_path   = os.path.join(script_dir, "ludo.py")
        config_path = os.path.join(script_dir, "game_config.json")

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(game_data, f, ensure_ascii=False, indent=2)
        except Exception as err:
            messagebox.showerror("Errore", f"Impossibile salvare:\n{err}")
            return

        if not os.path.isfile(ludo_path):
            messagebox.showerror("File non trovato",
                f"Non trovo 'ludo.py' in:\n{script_dir}")
            return

        try:
            subprocess.Popen([sys.executable, ludo_path, config_path])
        except Exception as err:
            messagebox.showerror("Errore avvio", f"{err}")
            return

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    StartScreen(root)
    root.mainloop()