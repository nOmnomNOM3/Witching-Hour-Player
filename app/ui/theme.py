from tkinter import ttk


BG = "#1c1c1e"
PANEL = "#2c2c2e"
FIELD = "#3a3a3c"
FG = "#f2f2f7"
MUTED = "#8e8e93"
ACCENT = "#0a84ff"
ACCENT_FG = "#ffffff"


def apply(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(".", background=BG, foreground=FG, fieldbackground=FIELD)
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Panel.TLabel", background=PANEL, foreground=FG)
    style.configure("Muted.TLabel", background=PANEL, foreground=MUTED)
    style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 20, "bold"))
    style.configure("TButton", background=FIELD, foreground=FG, padding=8)
    style.map("TButton", background=[("active", ACCENT)])
    style.configure("Accent.TButton", background=ACCENT, foreground=ACCENT_FG, padding=(18, 10))
    style.map("Accent.TButton", background=[("active", "#409cff")])
    style.configure("TRadiobutton", background=PANEL, foreground=FG)
    style.configure("TEntry", fieldbackground=FIELD, foreground=FG)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=PANEL, foreground=FG, padding=(16, 8))
    style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", ACCENT_FG)])



