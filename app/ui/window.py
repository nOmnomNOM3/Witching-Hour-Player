import os
import sys
import webbrowser

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import paths
from .. import settings as settings_mod
from ..library import Library, format_watch_entry, parse_watch_entry
from ..memory import Memory
from ..playback import build_playlist, remaining_session_items
from ..version import APP_VERSION, VERSION
from ..vlc import VLC_DOWNLOAD_URL, VlcSession, find_vlc, normalize_media_path

GITHUB_BRANCH = "https://github.com/nOmnomNOM3/Witching-Hour-Player/tree/nomnom"
GITHUB_BUGS = "https://github.com/nOmnomNOM3/Witching-Hour-Player/issues/new"

THEMES = {
    "modern": {
        "label": "Modern",
        "bg": "#1c1c1e",
        "panel": "rgba(44, 44, 46, 255)",
        "field": "#3a3a3c",
        "fg": "#f2f2f7",
        "muted": "#8e8e93",
        "accent": "#0a84ff",
        "accent_fg": "#ffffff",
        "glass": False,
    },
    "classic": {
        "label": "Classic",
        "bg": "#000000",
        "panel": "rgba(20, 10, 20, 255)",
        "field": "#1a0f08",
        "fg": "#ffffff",
        "muted": "#c9b8a8",
        "accent": "#ff7a00",
        "accent_fg": "#000000",
        "glass": False,
    },
    "waifu": {
        "label": "Waifu",
        "bg": "#1c1c1e",
        "panel": "rgba(28, 28, 30, 188)",
        "field": "rgba(58, 58, 60, 210)",
        "fg": "#f2f2f7",
        "muted": "#8e8e93",
        "accent": "#0a84ff",
        "accent_fg": "#ffffff",
        "glass": True,
    },
}



def first_existing(*names):
    for name in names:
        path = paths.asset_path(name)
        if os.path.isfile(path):
            return path
    return ""


class Backdrop(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg = QPixmap()
        self.character = QPixmap()

    def set_art(self, bg_path, char_path):
        self.bg = QPixmap(bg_path) if bg_path and os.path.isfile(bg_path) else QPixmap()
        self.character = (
            QPixmap(char_path) if char_path and os.path.isfile(char_path) else QPixmap()
        )
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#10182A"))
        if not self.bg.isNull():
            scaled = self.bg.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        if not self.character.isNull():
            max_h = int(self.height() * 0.92)
            scaled = self.character.scaledToHeight(max_h, Qt.SmoothTransformation)
            x = self.width() - scaled.width() - 8
            y = self.height() - scaled.height()
            painter.drawPixmap(x, y, scaled)


class QtAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = settings_mod.load_settings()
        self.settings["vlc_path"] = find_vlc(self.settings.get("vlc_path", ""))
        settings_mod.save_settings(self.settings)
        self.library = Library()
        self.memory = Memory()
        self.vlc = VlcSession()
        self.filtered = []
        self.theme_name = self.settings.get("theme", "modern")
        if self.theme_name not in THEMES:
            self.theme_name = "modern"

        self.setWindowTitle("Witching Hour")
        self.resize(1100, 780)
        self.setMinimumSize(QSize(960, 680))
        self._set_icon()

        self.stage = QWidget()
        self.setCentralWidget(self.stage)
        self.backdrop = Backdrop(self.stage)
        self.glass = QWidget(self.stage)
        self.glass.setObjectName("glass")

        self._build_menu()
        self._build_glass()
        self._apply_theme()
        self.refresh_library()
        if not self.settings.get("library_folders"):
            QTimer.singleShot(200, self.add_library)
        if not self.settings.get("vlc_path"):
            QTimer.singleShot(400, self.warn_missing_vlc)

        self.monitor = QTimer(self)
        self.monitor.setInterval(2000)
        self.monitor.timeout.connect(self._monitor)
        self.sleep_timer = QTimer(self)
        self.sleep_timer.setSingleShot(True)
        self.sleep_timer.timeout.connect(self._sleep_pause)
        self.episode_timer = QTimer(self)
        self.episode_timer.setInterval(1000)
        self.episode_timer.timeout.connect(self._poll_end_of_episode)

    def _set_icon(self):
        for name in ("app.ico", "app.png"):
            path = paths.asset_path(name)
            if os.path.isfile(path):
                self.setWindowIcon(QIcon(path))
                return

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Add library folder…", self.add_library)
        file_menu.addAction("Remove a library folder…", self.remove_library)
        file_menu.addAction("Clear all libraries…", self.clear_libraries)
        file_menu.addAction("Rescan library", self.refresh_library)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)

        view_menu = self.menuBar().addMenu("View")
        group = QActionGroup(self)
        group.setExclusive(True)
        for key, spec in THEMES.items():
            action = QAction(spec["label"], self, checkable=True)
            action.setChecked(key == self.theme_name)
            action.triggered.connect(lambda checked, name=key: self.set_theme(name))
            group.addAction(action)
            view_menu.addAction(action)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("About Witching Hour", self.show_about)

    def _build_glass(self):
        root = QVBoxLayout(self.glass)
        root.setContentsMargins(20, 16, 20, 12)
        root.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search shows")
        self.search.textChanged.connect(self.redraw_shows)
        root.addWidget(self.search)

        lists = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Shows"))
        self.show_list = QListWidget()
        self.show_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.show_list.setTextElideMode(Qt.ElideRight)
        self.show_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.show_list.itemSelectionChanged.connect(self.redraw_seasons)
        self.show_list.itemDoubleClicked.connect(lambda *_: self.add_selected())
        left.addWidget(self.show_list)
        left.addWidget(QLabel("Seasons"))
        self.season_list = QListWidget()
        self.season_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.season_list.setMaximumHeight(120)
        left.addWidget(self.season_list)
        lists.addLayout(left, 1)

        mid = QVBoxLayout()
        mid.addStretch()
        for text, fn in (
            ("Add →", self.add_selected),
            ("← Remove", self.remove_selected),
            ("Move up", lambda: self.move(-1)),
            ("Move down", lambda: self.move(1)),
            ("Clear", self.clear_order),
        ):
            button = QPushButton(text)
            button.clicked.connect(fn)
            mid.addWidget(button)
        mid.addStretch()
        lists.addLayout(mid)

        right = QVBoxLayout()
        right.addWidget(QLabel("Watch order"))
        self.order_list = QListWidget()
        self.order_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.order_list.setTextElideMode(Qt.ElideRight)
        right.addWidget(self.order_list)
        lists.addLayout(right, 1)
        root.addLayout(lists, 1)

        options = QHBoxLayout()
        count_box = QVBoxLayout()
        count_box.addWidget(QLabel("Episodes per show"))
        self.count = QLineEdit(str(self.settings.get("universal_count", 3)))
        self.count.setMaximumWidth(60)
        count_box.addWidget(self.count)
        options.addLayout(count_box)

        start_box = QVBoxLayout()
        start_box.addWidget(QLabel("Starting point"))
        self.start_memory = QRadioButton("Continue from memory")
        self.start_random = QRadioButton("Random start")
        group = QButtonGroup(self)
        group.addButton(self.start_memory)
        group.addButton(self.start_random)
        if self.settings.get("start_mode") == "random":
            self.start_random.setChecked(True)
        else:
            self.start_memory.setChecked(True)
        start_box.addWidget(self.start_memory)
        start_box.addWidget(self.start_random)
        options.addLayout(start_box)
        root.addLayout(options)

        info = QHBoxLayout()
        self.now_label = QLabel("Now playing: —")
        self.next_label = QLabel("Next: —")
        self.timer_label = QLabel("Sleep timer: off")
        info.addWidget(self.now_label)
        info.addWidget(self.next_label)
        info.addStretch()
        info.addWidget(self.timer_label)
        root.addLayout(info)

        sleep = QHBoxLayout()
        sleep.addWidget(QLabel("Sleep timer"))
        off = QPushButton("Off")
        off.clicked.connect(lambda: self.set_sleep("off"))
        sleep.addWidget(off)
        for minutes in (5, 10, 15, 30, 45, 60):
            button = QPushButton(f"{minutes}m")
            button.clicked.connect(lambda checked=False, value=minutes: self.set_sleep("minutes", value))
            sleep.addWidget(button)
        end = QPushButton("End of episode")
        end.clicked.connect(lambda: self.set_sleep("end_episode"))
        sleep.addWidget(end)
        self.custom_sleep = QLineEdit(str(self.settings.get("sleep_timer_minutes", 15)))
        self.custom_sleep.setMaximumWidth(50)
        sleep.addWidget(self.custom_sleep)
        custom = QPushButton("Custom min")
        custom.clicked.connect(self.apply_custom_sleep)
        sleep.addWidget(custom)
        sleep.addStretch()
        root.addLayout(sleep)

        play = QPushButton("Start playback")
        play.setObjectName("accent")
        play.clicked.connect(self.start)
        root.addWidget(play)
        self.status = QLabel("Ready.")
        root.addWidget(self.status)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_layers()

    def _layout_layers(self):
        area = self.stage.rect()
        self.backdrop.setGeometry(area)
        margin = 12
        right_gap = 260 if THEMES[self.theme_name]["glass"] else margin
        self.glass.setGeometry(
            margin,
            margin,
            max(1, area.width() - margin - right_gap),
            max(1, area.height() - margin * 2),
        )
        self.backdrop.lower()
        self.glass.raise_()

    def set_theme(self, name):
        if name not in THEMES:
            return
        self.theme_name = name
        self.settings["theme"] = name
        self.persist()
        self._apply_theme()

    def _apply_theme(self):
        colors = THEMES[self.theme_name]
        if colors["glass"]:
            self.backdrop.set_art(
                first_existing(
                    "waifu_bg_placeholder.png",
                    "waifu_bg.png",
                ),
                first_existing(
                    "waifu_mihanS.png",
                    "waifu_minahS.png",
                    "waifu_character.png",
                ),
            )
            self.backdrop.show()
        else:
            self.backdrop.set_art("", "")
            self.backdrop.hide()
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {colors['bg']}; color: {colors['fg']}; }}
            QMenuBar, QMenu {{ background: {colors['bg']}; color: {colors['fg']}; }}
            #glass {{
                background-color: {colors['panel']};
                border-radius: 14px;
            }}
            QLineEdit, QListWidget {{
                background: {colors['field']};
                color: {colors['fg']};
                border: none;
                padding: 6px;
            }}
            QListWidget::item:selected {{
                background: {colors['accent']};
                color: {colors['accent_fg']};
            }}
            QPushButton {{
                background: {colors['field']};
                color: {colors['fg']};
                border: none;
                padding: 8px 12px;
            }}
            QPushButton#accent {{
                background: {colors['accent']};
                color: {colors['accent_fg']};
                padding: 10px 18px;
            }}
            QLabel#title {{ font-size: 22px; font-weight: 700; }}
            QLabel#muted {{ color: {colors['muted']}; }}
            QScrollBar:vertical {{
                background: rgba(255, 255, 255, 36);
                width: 10px;
                margin: 0px;
                border: none;
                border-radius: 5px;
                }}
            QScrollBar::handle:vertical,
            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:vertical:pressed {{
                 min-height: 32px;
                border: none;
                border-radius: 5px;
                }}
            QScrollBar::handle:vertical {{
                background: #0a84ff;
                }}
            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:vertical:pressed {{
                background: #f2f2f7;
                }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                height: 0px;
                width: 0px;
                background: none;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: {colors['muted']};
                height: 10px;
                margin: 0px;
                border: none;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {colors['muted']};
                min-width: 32px;
                border: none;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {colors['accent']};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                height: 0px;
                width: 0px;
                background: none;
                border: none;
            }}
            QLabel#title {{ font-size: 22px; font-weight: 700; }}
            QLabel#muted {{ color: {colors['muted']}; }}
            """
        )
        self._refresh_timer_label()
        self._layout_layers()

    def persist(self):
        try:
            self.settings["universal_count"] = max(1, int(self.count.text()))
        except ValueError:
            pass
        self.settings["start_mode"] = "random" if self.start_random.isChecked() else "memory"
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
        self.status.setText(f"{len(self.library.shows)} shows")
        self.persist()

    def redraw_shows(self):
        query = self.search.text().strip().lower()
        if query:
            self.filtered = [show for show in self.library.shows if query in show.lower()]
        else:
            self.filtered = list(self.library.shows)
        self.show_list.clear()
        self.show_list.addItems(self.filtered)
        self.redraw_seasons()

    def redraw_seasons(self):
        self.season_list.clear()
        self.season_list.addItem("All seasons")
        items = self.show_list.selectedItems()
        if len(items) != 1:
            self.season_list.setCurrentRow(0)
            return
        show = items[0].text()
        for number in self.library.seasons_for(show):
            self.season_list.addItem(f"Season {number:02d}")
        self.season_list.setCurrentRow(0)

    def redraw_order(self):
        self.order_list.clear()
        self.order_list.addItems(self.settings.get("watch_order", []))

    def selected_season(self):
        item = self.season_list.currentItem()
        if item is None or item.text().lower().startswith("all"):
            return None
        digits = "".join(ch for ch in item.text() if ch.isdigit())
        return int(digits) if digits else None

    def add_selected(self):
        added = 0
        season = self.selected_season()
        for item in self.show_list.selectedItems():
            entry = format_watch_entry(item.text(), season)
            if entry not in self.settings["watch_order"]:
                self.settings["watch_order"].append(entry)
                added += 1
        self.redraw_order()
        self.persist()
        self.status.setText(f"Added {added} item(s)" if added else "Already in watch order")

    def remove_selected(self):
        row = self.order_list.currentRow()
        if row < 0:
            return
        del self.settings["watch_order"][row]
        self.redraw_order()
        self.persist()

    def move(self, delta):
        row = self.order_list.currentRow()
        dest = row + delta
        order = self.settings["watch_order"]
        if row < 0 or dest < 0 or dest >= len(order):
            return
        order[row], order[dest] = order[dest], order[row]
        self.redraw_order()
        self.order_list.setCurrentRow(dest)
        self.persist()

    def clear_order(self):
        self.settings["watch_order"] = []
        self.redraw_order()
        self.persist()

    def add_library(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a TV library folder")
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
            self.status.setText("No library folders to remove.")
            return
        path, _ok = QFileDialog.getOpenFileName(self, "Not used")
        # Simple chooser: pick from a list dialog
        from PySide6.QtWidgets import QInputDialog
        choice, ok = QInputDialog.getItem(
            self, "Remove library folder", "Folder", folders, 0, False
        )
        if not ok:
            return
        self.settings["library_folders"] = [item for item in folders if item != choice]
        self.refresh_library()

    def clear_libraries(self):
        if not self.settings.get("library_folders"):
            self.status.setText("Library is already empty.")
            return
        if QMessageBox.question(
            self,
            "Clear libraries",
            "Remove all library folders from Witching Hour?\n"
            "This does not delete video files.",
        ) != QMessageBox.Yes:
            return
        self.settings["library_folders"] = []
        self.settings["watch_order"] = []
        self.refresh_library()
        self.status.setText("Libraries cleared.")

    def browse_vlc(self):
        path, _ok = QFileDialog.getOpenFileName(
            self, "Locate vlc.exe", "", "VLC (vlc.exe);;Programs (*.exe);;All files (*.*)"
        )
        if not path:
            return
        self.settings["vlc_path"] = os.path.normpath(path)
        self.persist()
        self.status.setText(f"Using VLC at {path}")

    def warn_missing_vlc(self):
        box = QMessageBox(self)
        box.setWindowTitle("VLC required")
        box.setText(
            "Witching Hour could not find VLC.\n"
            "Install it, or point this app at vlc.exe."
        )
        download = box.addButton("Download VLC", QMessageBox.AcceptRole)
        locate = box.addButton("Locate vlc.exe…", QMessageBox.ActionRole)
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == download:
            webbrowser.open(VLC_DOWNLOAD_URL)
        elif box.clickedButton() == locate:
            self.browse_vlc()

    def show_about(self):
        box = QMessageBox(self)
        box.setWindowTitle("About Witching Hour")
        box.setText(f"Witching Hour\nVersion {APP_VERSION}\n\nQt preview UI.")
        repo = box.addButton("GitHub", QMessageBox.ActionRole)
        bugs = box.addButton("Report a bug", QMessageBox.ActionRole)
        box.addButton("Close", QMessageBox.AcceptRole)
        box.exec()
        if box.clickedButton() == repo:
            webbrowser.open(GITHUB_BRANCH)
        elif box.clickedButton() == bugs:
            webbrowser.open(GITHUB_BUGS)

    def apply_custom_sleep(self):
        try:
            minutes = int(self.custom_sleep.text())
            if minutes < 1 or minutes > 1440:
                raise ValueError
        except ValueError:
            self.status.setText("Enter minutes between 1 and 1440.")
            return
        self.set_sleep("minutes", minutes)

    def set_sleep(self, mode, minutes=None):
        self.settings["sleep_timer_mode"] = mode
        if minutes is not None:
            self.settings["sleep_timer_minutes"] = int(minutes)
            self.custom_sleep.setText(str(int(minutes)))
        self.persist()
        self._refresh_timer_label()
        if self.vlc.running():
            self._arm_sleep_timer()

    def _refresh_timer_label(self):
        mode = self.settings.get("sleep_timer_mode", "off")
        if mode == "off":
            self.timer_label.setText("Sleep timer: off")
        elif mode == "end_episode":
            self.timer_label.setText("Sleep timer: end of episode")
        else:
            self.timer_label.setText(
                f"Sleep timer: {self.settings.get('sleep_timer_minutes', 15)} min"
            )

    def _arm_sleep_timer(self):
        self.sleep_timer.stop()
        self.episode_timer.stop()
        mode = self.settings.get("sleep_timer_mode", "off")
        if mode == "off":
            return
        if mode == "end_episode":
            self.episode_timer.start()
            return
        minutes = int(self.settings.get("sleep_timer_minutes", 15))
        self.sleep_timer.start(minutes * 60 * 1000)

    def _poll_end_of_episode(self):
        if self.settings.get("sleep_timer_mode") != "end_episode":
            self.episode_timer.stop()
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

    def start(self):
        path = find_vlc(self.settings.get("vlc_path", ""))
        self.settings["vlc_path"] = path
        if not path:
            self.warn_missing_vlc()
            return
        if self.vlc.running():
            QMessageBox.information(self, "Playback", "VLC is already running.")
            return
        if self.memory.valid_session():
            choice = QMessageBox.question(
                self,
                "Resume?",
                "An unfinished playlist was found.\nYes = resume\nNo = start a new playlist",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if choice == QMessageBox.Cancel:
                return
            if choice == QMessageBox.Yes:
                self._launch(remaining_session_items(self.memory.session))
                return
            self.memory.clear_session()
        if not self.settings.get("watch_order"):
            self.status.setText("Add at least one show to the watch order.")
            return
        try:
            count = max(1, int(self.count.text()))
        except ValueError:
            self.status.setText("Enter a valid episode count.")
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
            self.status.setText("No episodes could be selected.")
            return
        self._launch(items)

    def _launch(self, items):
        try:
            self.vlc.launch(self.settings["vlc_path"], items)
        except OSError as error:
            QMessageBox.critical(self, "Playback", str(error))
            return
        self.memory.save_session(items, 0, items[0].get("resume_time", 0))
        self._update_now(0)
        self.status.setText(f"Playing {len(items)} episode(s)")
        self.monitor.start()
        QTimer.singleShot(1500, self._arm_sleep_timer)

    def _update_now(self, index):
        items = self.memory.session.get("items", [])
        if not items or index >= len(items):
            return
        item = items[index]
        self.now_label.setText(
            f"Now playing: {item.get('show')} "
            f"S{int(item.get('season', 1)):02d}E{int(item.get('episode', 1)):02d}"
        )
        if index + 1 < len(items):
            nxt = items[index + 1]
            self.next_label.setText(
                f"Next: {nxt.get('show')} "
                f"S{int(nxt.get('season', 1)):02d}E{int(nxt.get('episode', 1)):02d}"
            )
        else:
            self.next_label.setText("Next: end of lineup")

    def _monitor(self):
        items = self.memory.session.get("items", [])
        if not items:
            self.monitor.stop()
            return
        if self.vlc.process is not None and self.vlc.process.poll() is not None:
            self.status.setText("VLC closed. Position saved.")
            self.monitor.stop()
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
            self.status.setText("Playlist finished.")
            self.monitor.stop()

    def _sleep_pause(self):
        self.episode_timer.stop()
        if self.vlc.pause():
            self.status.setText("Sleep timer paused VLC.")
            self.timer_label.setText("Sleep timer: done")

    def closeEvent(self, event):
        self.persist()
        event.accept()

    @staticmethod
    def run():
        app = QApplication.instance() or QApplication(sys.argv)
        app.setStyle("Fusion")
        window = QtAppWindow()
        window.show()
        sys.exit(app.exec())