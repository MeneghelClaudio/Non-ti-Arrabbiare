import sys
import os

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    base = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(os.path.join(base, "assets")):
        return base
    return os.path.dirname(base)

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, root_dir)
    
    base = get_base_path()
    os.chdir(base)

    for mod in ["ludo", "sound", "end_screen", "hud", "draw", "pedine", "celle", "player", "logica", "costanti", "bot_ai", "dado"]:
        try:
            __import__(mod)
        except Exception as e:
            print(f"Import {mod}: {e}")

    import tkinter as tk
    from start_screen import StartScreen
    root = tk.Tk()
    app = StartScreen(root)
    root.mainloop()

if __name__ == "__main__":
    main()