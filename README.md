# Witching Hour

Local night-mode TV player. Point it at folders of video files, build a short
watch order, play in VLC, resume later, and pause on a sleep timer.

It does **not** talk to Netflix, Max, or any other streaming service.

## Why this rewrite

The original was a single ~6–7k line GPT script: Halloween theme, everything
in one file, settings and playback mixed with widgets. This layout keeps the
same job but splits work by responsibility so you can change the scanner
without touching the window.

```
witching_hour/
  main.py              # start here
  app/
    paths.py           # config file locations
    store.py           # JSON load/save
    settings.py
    vlc.py             # find VLC, launch, RC socket
    library.py         # folder walk, seasons, filename parse
    memory.py          # per-show cursor + unfinished session
    playback.py        # build playlist + monitor
    ui/
      theme.py
      window.py        # ttk UI
```

## Requirements

- Windows (VLC path discovery is Windows-oriented; the rest is plain Python)
- Python 3.10+
- VLC ([videolan.org/vlc](https://www.videolan.org/vlc/))
- Standard library only (`tkinter`, `json`, `socket`, …)

```bat
python main.py
```

## Player: VLC vs mpv

**Keep VLC as the default.** You already depend on it, it decodes everything,
and users can install it in two clicks. This app talks to it over the RC
interface (`get_time`, `pause`, current file).

**mpv is the better long-term embed** if you want a player *inside* the window
or tighter IPC (`--input-ipc-server` JSON). Use mpv when you outgrow “launch
an external playlist.” Do not switch just to switch.

UWP is not a good fit. It is a C# / XAML store-app model, not something you
wrap around this Python project. If you ever want a native Windows shell,
that is a separate WinUI 3 app, not a restyle of this repo.

## How it behaves

1. Add one or more library roots (a show folder, a folder of shows, or a
   parent with category folders).
2. Immediate children that are only containers are walked. Folders with video
   or season-shaped children become shows.
3. Select a show, optionally a season, add to the watch order.
4. Start: N episodes per show, from memory or a random start, handed to VLC.
5. Position is polled every 2 seconds. Closing VLC early keeps an unfinished
   session. Sleep timer can pause VLC after N minutes or at end of episode.

## Data files (next to `main.py` or the exe)

| File | Role |
|---|---|
| `settings.json` | libraries, VLC path, counts, timer |
| `playback_memory.json` | season / episode / seconds per show |
| `unfinished_session.json` | mid-playlist snapshot |
| `watch_history.json` | what was sent to VLC |
