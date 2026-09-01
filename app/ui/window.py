import os
import webbrowser
from tkinter import Listbox, Menu, StringVar, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk

from .. import settings as settings_mod
from ..library import Library, format_watch_entry, parse_watch_entry
from ..memory import Memory
from ..playback import build_playlist, remaining_session_items
from ..vlc import VLC_DOWNLOAD_URL, VlcSession, find_vlc, normalize_media_path
from . import theme


class AppWindow:
    def __init__(self):
        self.settings = settings_mod.load_settings()
        self.settings["vlc_path"] = find_vlc(self.settings.get("vlc_path", ""))
        settings_mod.save_settings(self.settings)

        self.library = Library()
        self.memory = Memory()
        self.vlc = VlcSession()
        self.filtered = []
        self.monitor_id = None
        self.timer_id = None
        self.episode_timer_id = None

        self.root = Tk()
        self.root.title("Witching Hour")
        self.root.geometry("1100x780")
        self.root.minsize(960, 680)
        theme.apply(self.root, self.settings.get("theme", "modern"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.custom_timer_var = StringVar(
            value=str(self.settings.get("sleep_timer_minutes", 15))
        )
        self.status = StringVar(value="Ready.")
        self.count_var = StringVar(value=str(self.settings.get("universal_count", 3)))
        self.mode_var = StringVar(value=self.settings.get("episode_mode", "universal"))
        self.start_var = StringVar(value=self.settings.get("start_mode", "memory"))
        self.search_var = StringVar()
        self.now_var = StringVar(value="Now playing: —")
        self.next_var = StringVar(value="Next: —")
        self.timer_var = StringVar(value="Sleep timer: off")

        self._build_menu()
        self._build_layout()
        self._refresh_timer_label()
        self.refresh_library()
        if not self.settings["vlc_path"]:
            self.root.after(400, self.warn_missing_vlc)

    def _build_menu(self):
        menu = Menu(self.root)
        file_menu = Menu(menu, tearoff=0)
        file_menu.add_command(label="Add library folder…", command=self.add_library)
        file_menu.add_command(label="Remove a library folder…", command=self.remove_library)
        file_menu.add_command(label="Clear all libraries…", command=self.clear_libraries)
        file_menu.add_command(label="Rescan library", command=self.refresh_library)
        file_menu.add_separator()
        file_menu.add_command(label="Sleep timer…", command=self.sleep_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menu.add_cascade(label="File", menu=file_menu)

        view_menu = Menu(menu, tearoff=0)
        self.theme_var = StringVar(value=theme.normalize_name(self.settings.get("theme", "modern")))
        for key, spec in theme.THEMES.items():
            view_menu.add_radiobutton(
                label=spec["label"],
                value=key,
                variable=self.theme_var,
                command=lambda name=key: self.set_theme(name),
            )
        menu.add_cascade(label="View", menu=view_menu)

        help_menu = Menu(menu, tearoff=0)
        help_menu.add_command(label="About Witching Hour", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu)

    def _build_layout(self):
        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=20, pady=(16, 8))
        ttk.Label(header, text="Witching Hour", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Local folders → short playlist → VLC",
            foreground=theme.MUTED,
            background=theme.BG,
        ).pack(anchor="w", pady=(2, 0))

        search = ttk.Frame(self.root)
        search.pack(fill="x", padx=20, pady=(0, 8))
        ttk.Entry(search, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        self.search_var.trace_add("write", lambda *_: self.redraw_shows())

        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=20)

        left = ttk.Frame(body, style="Panel.TFrame")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        ttk.Label(left, text="Shows", style="Panel.TLabel").pack(anchor="w", padx=12, pady=(10, 4))
        self.show_list = Listbox(
            left,
            selectmode="extended",
            exportselection=False,
            bg=theme.FIELD,
            fg=theme.FG,
            selectbackground=theme.ACCENT,
            selectforeground=theme.ACCENT_FG,
            highlightthickness=0,
            borderwidth=0,
            font=("Segoe UI", 11),
        )
        self.show_list.pack(fill="both", expand=True, padx=12)
        self.show_list.bind("<<ListboxSelect>>", lambda e: self.redraw_seasons())
        self.show_list.bind("<Double-Button-1>", lambda e: self.add_selected())

        ttk.Label(left, text="Seasons", style="Muted.TLabel").pack(anchor="w", padx=12, pady=(8, 2))
        self.season_list = Listbox(
            left,
            height=5,
            exportselection=False,
            bg=theme.FIELD,
            fg=theme.FG,
            selectbackground=theme.ACCENT,
            selectforeground=theme.ACCENT_FG,
            highlightthickness=0,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        self.season_list.pack(fill="x", padx=12, pady=(0, 12))

        mid = ttk.Frame(body)
        mid.pack(side="left", padx=6)
        ttk.Button(mid, text="Add →", command=self.add_selected).pack(pady=4)
        ttk.Button(mid, text="← Remove", command=self.remove_selected).pack(pady=4)
        ttk.Button(mid, text="Move up", command=lambda: self.move(-1)).pack(pady=4)
        ttk.Button(mid, text="Move down", command=lambda: self.move(1)).pack(pady=4)
        ttk.Button(mid, text="Clear", command=self.clear_order).pack(pady=12)

        right = ttk.Frame(body, style="Panel.TFrame")
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        ttk.Label(right, text="Watch order", style="Panel.TLabel").pack(anchor="w", padx=12, pady=(10, 4))
        self.order_list = Listbox(
            right,
            selectmode="single",
            exportselection=False,
            bg=theme.FIELD,
            fg=theme.FG,
            selectbackground=theme.ACCENT,
            selectforeground=theme.ACCENT_FG,
            highlightthickness=0,
            borderwidth=0,
            font=("Segoe UI", 11),
        )
        self.order_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        options = ttk.Frame(self.root)
        options.pack(fill="x", padx=20, pady=10)
        count_panel = ttk.Frame(options, style="Panel.TFrame")
        count_panel.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Label(count_panel, text="Episodes per show", style="Panel.TLabel").pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        ttk.Entry(count_panel, textvariable=self.count_var, width=6).pack(anchor="w", padx=12, pady=(0, 10))

        start_panel = ttk.Frame(options, style="Panel.TFrame")
        start_panel.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ttk.Label(start_panel, text="Starting point", style="Panel.TLabel").pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        ttk.Radiobutton(
            start_panel, text="Continue from memory", variable=self.start_var, value="memory"
        ).pack(anchor="w", padx=12)
        ttk.Radiobutton(
            start_panel, text="Random start", variable=self.start_var, value="random"
        ).pack(anchor="w", padx=12, pady=(0, 10))

        info = ttk.Frame(self.root, style="Panel.TFrame")
        info.pack(fill="x", padx=20)
        ttk.Label(info, textvariable=self.now_var, style="Panel.TLabel").pack(side="left", padx=12, pady=8)
        ttk.Label(info, textvariable=self.next_var, style="Muted.TLabel").pack(side="left", padx=12)
        ttk.Label(info, textvariable=self.timer_var, style="Muted.TLabel").pack(side="right", padx=12)

        sleep_row = ttk.Frame(self.root)
        sleep_row.pack(fill="x", padx=20, pady=(10, 0))
        ttk.Label(sleep_row, text="Sleep timer").pack(side="left", padx=(0, 8))
        ttk.Button(sleep_row, text="Off", command=lambda: self.set_sleep("off")).pack(side="left", padx=2)
        for minutes in (5, 10, 15, 30, 45, 60):
            ttk.Button(
                sleep_row,
                text=f"{minutes}m",
                command=lambda value=minutes: self.set_sleep("minutes", value),
            ).pack(side="left", padx=2)
        ttk.Button(
            sleep_row,
            text="End of episode",
            command=lambda: self.set_sleep("end_episode"),
        ).pack(side="left", padx=8)
        ttk.Entry(sleep_row, textvariable=self.custom_timer_var, width=5).pack(side="left")
        ttk.Button(sleep_row, text="Custom min", command=self.apply_custom_sleep).pack(
            side="left", padx=4
        )

        ttk.Button(self.root, text="Start playback", style="Accent.TButton", command=self.start).pack(
            pady=12
        )
        ttk.Label(self.root, textvariable=self.status).pack(anchor="w", padx=20, pady=(0, 12))

    def persist(self):
        try:
            self.settings["universal_count"] = max(1, int(self.count_var.get()))
        except ValueError:
            pass
        self.settings["start_mode"] = self.start_var.get()
        self.settings["episode_mode"] = self.mode_var.get()
        settings_mod.save_settings(self.settings)

    def refresh_library(self):
        self.library.scan(self.settings.get("library_folders", []))
        kept = []
        for entry in self.settings.get("watch_order", []):
            show, _season = parse_watch_entry(entry)
            if show in self.library.paths:
                kept.append(entry)
        self.settings["watch_order"] = kept
        self.redraw_shows()
        self.redraw_order()
        self.status.set(f"{len(self.library.shows)} shows")
        self.persist()

    def redraw_shows(self):
        query = self.search_var.get().strip().lower()
        if query:
            self.filtered = [show for show in self.library.shows if query in show.lower()]
        else:
            self.filtered = list(self.library.shows)
        self.show_list.delete(0, "end")
        for show in self.filtered:
            self.show_list.insert("end", show)
        self.redraw_seasons()

    def redraw_seasons(self):
        self.season_list.delete(0, "end")
        self.season_list.insert("end", "All seasons")
        selected = self.show_list.curselection()
        if len(selected) != 1:
            self.season_list.selection_set(0)
            return
        show = self.filtered[selected[0]]
        for number in self.library.seasons_for(show):
            self.season_list.insert("end", f"Season {number:02d}")
        self.season_list.selection_set(0)

    def redraw_order(self):
        self.order_list.delete(0, "end")
        for entry in self.settings.get("watch_order", []):
            self.order_list.insert("end", entry)

    def selected_season(self):
        choice = self.season_list.curselection()
        if not choice:
            return None
        label = self.season_list.get(choice[0])
        if label.lower().startswith("all"):
            return None
        digits = "".join(ch for ch in label if ch.isdigit())
        return int(digits) if digits else None

    def add_selected(self):
        added = 0
        season = self.selected_season()
        for index in self.show_list.curselection():
            show = self.filtered[index]
            entry = format_watch_entry(show, season)
            if entry not in self.settings["watch_order"]:
                self.settings["watch_order"].append(entry)
                added += 1
        self.redraw_order()
        self.persist()
        self.status.set(f"Added {added} item(s)" if added else "Already in watch order")

    def remove_selected(self):
        selected = self.order_list.curselection()
        if not selected:
            return
        del self.settings["watch_order"][selected[0]]
        self.redraw_order()
        self.persist()

    def move(self, delta):
        selected = self.order_list.curselection()
        if not selected:
            return
        index = selected[0]
        dest = index + delta
        order = self.settings["watch_order"]
        if dest < 0 or dest >= len(order):
            return
        order[index], order[dest] = order[dest], order[index]
        self.redraw_order()
        self.order_list.selection_set(dest)
        self.persist()

    def clear_order(self):
        self.settings["watch_order"] = []
        self.redraw_order()
        self.persist()

    def set_theme(self, name):
        name = theme.apply(self.root, name)
        self.settings["theme"] = name
        self.theme_var.set(name)
        self._paint_lists()
        self.persist()

    def _paint_lists(self):
        for widget in (self.show_list, self.season_list, self.order_list):
            theme.paint_listbox(widget)

    def show_about(self):
        dialog = Toplevel(self.root)
        dialog.title("About Witching Hour")
        dialog.configure(bg=theme.BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        ttk.Label(dialog, text="Witching Hour", style="Title.TLabel").pack(padx=24, pady=(18, 4))
        ttk.Label(dialog, text=f"Version {theme.APP_VERSION}").pack()
        ttk.Label(
            dialog,
            text="Local folder playback. No streaming services.",
        ).pack(padx=24, pady=(8, 12))
        ttk.Button(
            dialog,
            text="GitHub repository",
            command=lambda: webbrowser.open(theme.GITHUB_BRANCH),
        ).pack(fill="x", padx=24, pady=3)
        ttk.Button(
            dialog,
            text="Submit a bug report",
            command=lambda: webbrowser.open(theme.GITHUB_BUGS),
        ).pack(fill="x", padx=24, pady=3)
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=(12, 18))

    def add_library(self):

        folder = filedialog.askdirectory(title="Choose a TV library folder")
        if not folder:
            return
        folder = os.path.normpath(folder)
        folders = self.settings.setdefault("library_folders", [])
        if folder not in folders:
            folders.append(folder)
        self.refresh_library()

    def remove_library(self):
        folders = list(self.settings.get("library_folders", []))
        if not folders:
            self.status.set("No library folders to remove.")
            return
        dialog = Toplevel(self.root)
        dialog.title("Remove library folder")
        dialog.configure(bg=theme.BG)
        dialog.transient(self.root)
        ttk.Label(dialog, text="Select a folder to remove").pack(padx=16, pady=(12, 6))
        listing = Listbox(
            dialog,
            exportselection=False,
            bg=theme.FIELD,
            fg=theme.FG,
            selectbackground=theme.ACCENT,
            height=min(8, max(3, len(folders))),
        )
        listing.pack(fill="both", expand=True, padx=16)
        for folder in folders:
            listing.insert("end", folder)

        def drop():
            selected = listing.curselection()
            if not selected:
                return
            folder = folders[selected[0]]
            self.settings["library_folders"] = [
                item for item in self.settings.get("library_folders", []) if item != folder
            ]
            self.refresh_library()
            dialog.destroy()

        ttk.Button(dialog, text="Remove", command=drop).pack(pady=12)

    def clear_libraries(self):
        folders = self.settings.get("library_folders", [])
        if not folders:
            self.status.set("Library is already empty.")
            return
        if not messagebox.askyesno(
            "Clear libraries",
            "Remove all library folders from Witching Hour?\n\n"
            "This does not delete video files. It only forgets the folders "
            "this app is pointed at.",
        ):
            return
        self.settings["library_folders"] = []
        self.settings["watch_order"] = []
        self.refresh_library()
        self.status.set("Libraries cleared. Add a folder to start over.")

    def browse_vlc(self):
        path = filedialog.askopenfilename(
            title="Locate vlc.exe",
            filetypes=[("VLC", "vlc.exe"), ("Programs", "*.exe"), ("All files", "*.*")],
        )
        if not path:
            return
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            messagebox.showerror("VLC", "That file does not exist.")
            return
        self.settings["vlc_path"] = path
        self.persist()
        self.status.set(f"Using VLC at {path}")

    def warn_missing_vlc(self):
        dialog = Toplevel(self.root)
        dialog.title("VLC required")
        dialog.configure(bg=theme.BG)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        ttk.Label(
            dialog,
            text=(
                "Witching Hour could not find VLC.\n\n"
                "Checked:\n"
                "• The saved path in settings\n"
                "• Program Files and Program Files (x86)\n"
                "• vlc.exe on PATH\n\n"
                "Install VLC, or point this app at vlc.exe."
            ),
            justify="left",
        ).pack(padx=20, pady=(16, 8))
        row = ttk.Frame(dialog)
        row.pack(pady=(0, 16))
        ttk.Button(
            row,
            text="Download VLC",
            command=lambda: webbrowser.open(VLC_DOWNLOAD_URL),
        ).pack(side="left", padx=6)
        ttk.Button(
            row,
            text="Locate vlc.exe…",
            command=lambda: (dialog.destroy(), self.browse_vlc()),
        ).pack(side="left", padx=6)
        ttk.Button(row, text="Cancel", command=dialog.destroy).pack(side="left", padx=6)

    def sleep_dialog(self):
        dialog = Toplevel(self.root)
        dialog.title("Sleep timer")
        dialog.configure(bg=theme.BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        ttk.Label(dialog, text="Pause VLC after").pack(padx=20, pady=(16, 8))

        row = ttk.Frame(dialog)
        row.pack(padx=20)
        ttk.Button(row, text="Off", command=lambda: self._pick_sleep(dialog, "off")).pack(
            fill="x", pady=2
        )
        for minutes in (5, 10, 15, 30, 45, 60):
            ttk.Button(
                row,
                text=f"{minutes} minutes",
                command=lambda value=minutes: self._pick_sleep(dialog, "minutes", value),
            ).pack(fill="x", pady=2)
        ttk.Button(
            row,
            text="End of current episode",
            command=lambda: self._pick_sleep(dialog, "end_episode"),
        ).pack(fill="x", pady=2)

        custom = ttk.Frame(dialog)
        custom.pack(padx=20, pady=(8, 16), fill="x")
        ttk.Entry(custom, textvariable=self.custom_timer_var, width=6).pack(side="left")
        ttk.Button(
            custom,
            text="Use custom minutes",
            command=lambda: self._pick_custom(dialog),
        ).pack(side="left", padx=8)

    def _pick_sleep(self, dialog, mode, minutes=None):
        self.set_sleep(mode, minutes)
        dialog.destroy()

    def _pick_custom(self, dialog):
        if self.apply_custom_sleep():
            dialog.destroy()

    def apply_custom_sleep(self):
        try:
            minutes = int(self.custom_timer_var.get())
            if minutes < 1 or minutes > 1440:
                raise ValueError
        except ValueError:
            self.status.set("Enter minutes between 1 and 1440.")
            return False
        self.set_sleep("minutes", minutes)
        return True

    def set_sleep(self, mode, minutes=None):
        self.settings["sleep_timer_mode"] = mode
        if minutes is not None:
            self.settings["sleep_timer_minutes"] = int(minutes)
            self.custom_timer_var.set(str(int(minutes)))
        self.persist()
        self._refresh_timer_label()
        if self.vlc.running():
            self._arm_sleep_timer()
        if mode == "off":
            self.status.set("Sleep timer off.")
        elif mode == "end_episode":
            self.status.set("Sleep timer will pause at the end of the current file.")
        else:
            self.status.set(
                f"Sleep timer set for {self.settings['sleep_timer_minutes']} minutes."
            )

    def _refresh_timer_label(self):
        mode = self.settings.get("sleep_timer_mode", "off")
        if mode == "off":
            self.timer_var.set("Sleep timer: off")
        elif mode == "end_episode":
            self.timer_var.set("Sleep timer: end of episode")
        else:
            self.timer_var.set(
                f"Sleep timer: {self.settings.get('sleep_timer_minutes', 15)} min"
            )

    def _cancel_sleep_timer(self):
        if self.timer_id is not None:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None
        if self.episode_timer_id is not None:
            try:
                self.root.after_cancel(self.episode_timer_id)
            except Exception:
                pass
            self.episode_timer_id = None

    def _arm_sleep_timer(self):
        self._cancel_sleep_timer()
        mode = self.settings.get("sleep_timer_mode", "off")
        if mode == "off":
            return
        if mode == "end_episode":
            self._poll_end_of_episode()
            return
        minutes = int(self.settings.get("sleep_timer_minutes", 15))
        self.timer_id = self.root.after(minutes * 60 * 1000, self._sleep_pause)

    def _poll_end_of_episode(self):
        if self.settings.get("sleep_timer_mode") != "end_episode":
            return
        current_time = self.vlc.current_time()
        total = self.vlc.current_length()
        if (
            current_time is not None
            and total is not None
            and total > 5
            and 0 <= (total - current_time) <= 2
        ):
            self._sleep_pause()
            return
        self.episode_timer_id = self.root.after(1000, self._poll_end_of_episode)

    def start(self):
        path = find_vlc(self.settings.get("vlc_path", ""))
        self.settings["vlc_path"] = path
        if not path:
            self.warn_missing_vlc()
            return
        if self.vlc.running():
            messagebox.showinfo("Playback", "VLC is already running.")
            return

        if self.memory.valid_session():
            choice = messagebox.askyesnocancel(
                "Resume?",
                "An unfinished playlist was found.\nYes = resume\nNo = start a new playlist",
            )
            if choice is None:
                return
            if choice:
                items = remaining_session_items(self.memory.session)
                self._launch(items)
                return
            self.memory.clear_session()

        if not self.settings.get("watch_order"):
            self.status.set("Add at least one show to the watch order.")
            return
        try:
            count = max(1, int(self.count_var.get()))
        except ValueError:
            self.status.set("Enter a valid episode count.")
            return
        self.persist()
        items = build_playlist(
            self.settings["watch_order"],
            self.library,
            self.memory,
            self.settings,
            count,
        )
        if not items:
            self.status.set("No episodes could be selected.")
            return
        self._launch(items)

    def _launch(self, items):
        try:
            self.vlc.launch(self.settings["vlc_path"], items)
        except OSError as error:
            messagebox.showerror("Playback", str(error))
            return
        self.memory.save_session(items, 0, items[0].get("resume_time", 0))
        self._update_now(0)
        self.status.set(f"Playing {len(items)} episode(s)")
        self.root.after(1800, self._monitor)
        self.root.after(1500, self._arm_sleep_timer)

    def _update_now(self, index):
        items = self.memory.session.get("items", [])
        if not items or index >= len(items):
            return
        item = items[index]
        self.now_var.set(
            f"Now playing: {item.get('show')} S{int(item.get('season', 1)):02d}E{int(item.get('episode', 1)):02d}"
        )
        if index + 1 < len(items):
            nxt = items[index + 1]
            self.next_var.set(
                f"Next: {nxt.get('show')} S{int(nxt.get('season', 1)):02d}E{int(nxt.get('episode', 1)):02d}"
            )
        else:
            self.next_var.set("Next: end of lineup")

    def _monitor(self):
        items = self.memory.session.get("items", [])
        if not items:
            return
        if self.vlc.process is not None and self.vlc.process.poll() is not None:
            self.status.set("VLC closed. Position saved.")
            return

        current_path = self.vlc.current_path()
        current_time = self.vlc.current_time()
        current_length = self.vlc.current_length()
        index = self.memory.session.get("current_index", 0)

        if current_path:
            for candidate, item in enumerate(items):
                if normalize_media_path(item.get("path", "")) == current_path:
                    if candidate > index:
                        for done in items[index:candidate]:
                            self.memory.advance(done)
                    index = candidate
                    self.memory.session["current_index"] = index
                    break

        if current_time is not None and 0 <= index < len(items):
            self.memory.session["current_time"] = max(0, int(current_time))
            self.memory.interrupt(items[index], current_time)
            self.memory.save_session(items, index, current_time)
            self._update_now(index)

        if (
            index == len(items) - 1
            and current_time is not None
            and current_length is not None
            and current_length > 5
            and current_time >= current_length - 2
        ):
            self.memory.advance(items[index])
            self.memory.clear_session()
            self.status.set("Playlist finished.")
            return

        self.monitor_id = self.root.after(2000, self._monitor)

    def _sleep_pause(self):
        if self.vlc.pause():
            self.status.set("Sleep timer paused VLC.")
            self.timer_var.set("Sleep timer: done")

    def on_close(self):
        self.persist()
        self.root.destroy()

    def run(self):
        if not self.settings.get("library_folders"):
            self.root.after(200, self.add_library)
        self.root.mainloop()
