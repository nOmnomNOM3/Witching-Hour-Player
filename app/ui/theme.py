from tkinter import ttk

from ..version import APP_VERSION
GITHUB_REPO = "https://github.com/nOmnomNOM3/Witching-Hour-Player"
GITHUB_BRANCH = "https://github.com/nOmnomNOM3/Witching-Hour-Player/tree/nomnom"
GITHUB_BUGS = "https://github.com/nOmnomNOM3/Witching-Hour-Player/issues/new"

THEMES = {
    "modern": {
        "label": "Modern",
        "BG": "#1c1c1e",
        "PANEL": "#2c2c2e",
        "FIELD": "#3a3a3c",
        "FG": "#f2f2f7",
        "MUTED": "#8e8e93",
        "ACCENT": "#0a84ff",
        "ACCENT_FG": "#ffffff",
        "ACCENT_HOVER": "#409cff",
    },
    "classic": {
        "label": "Classic",
        "BG": "#000000",
        "PANEL": "#140a14",
        "FIELD": "#1a0f08",
        "FG": "#ffffff",
        "MUTED": "#c9b8a8",
        "ACCENT": "#ff7a00",
        "ACCENT_FG": "#000000",
        "ACCENT_HOVER": "#ff9a33",
    },
    "waifu": {
        "label": "Waifu",
        "BG": "#2a1624",
        "PANEL": "#3d2233",
        "FIELD": "#4a2a3e",
        "FG": "#fff0f6",
        "MUTED": "#e7a7c4",
        "ACCENT": "#ff7eb6",
        "ACCENT_FG": "#2a1020",
        "ACCENT_HOVER": "#ffa3cc",
    },
}

BG = THEMES["modern"]["BG"]
PANEL = THEMES["modern"]["PANEL"]
FIELD = THEMES["modern"]["FIELD"]
FG = THEMES["modern"]["FG"]
MUTED = THEMES["modern"]["MUTED"]
ACCENT = THEMES["modern"]["ACCENT"]
ACCENT_FG = THEMES["modern"]["ACCENT_FG"]
ACCENT_HOVER = THEMES["modern"]["ACCENT_HOVER"]
CURRENT = "modern"


def normalize_name(name):
    if name in THEMES:
        return name
    return "modern"


def apply(root, name="modern"):
    global BG, PANEL, FIELD, FG, MUTED, ACCENT, ACCENT_FG, ACCENT_HOVER, CURRENT
    CURRENT = normalize_name(name)
    colors = THEMES[CURRENT]
    BG = colors["BG"]
    PANEL = colors["PANEL"]
    FIELD = colors["FIELD"]
    FG = colors["FG"]
    MUTED = colors["MUTED"]
    ACCENT = colors["ACCENT"]
    ACCENT_FG = colors["ACCENT_FG"]
    ACCENT_HOVER = colors["ACCENT_HOVER"]

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
    style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])
    style.configure("TRadiobutton", background=PANEL, foreground=FG)
    style.configure("TEntry", fieldbackground=FIELD, foreground=FG)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=PANEL, foreground=FG, padding=(16, 8))
    style.map(
        "TNotebook.Tab",
        background=[("selected", ACCENT)],
        foreground=[("selected", ACCENT_FG)],
    )
    return CURRENT


def paint_listbox(widget):
    widget.configure(
        bg=FIELD,
        fg=FG,
        selectbackground=ACCENT,
        selectforeground=ACCENT_FG,
        highlightbackground=PANEL,
    )