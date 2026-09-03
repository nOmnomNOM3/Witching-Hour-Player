import os
import sys
import webbrowser

from PySide6.QtCore import Qt, QTimer, QSize, QEvent
from PySide6.QtGui import QAction, QActionGroup, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QPlainTextEdit,
    QSizePolicy,
    QStackedLayout,
    QTabWidget,
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



def _asset_roots():
    roots = [
        os.path.join(paths.bundle_folder(), "assets"),
        os.path.join(paths.program_folder(), "assets"),
        os.path.join(os.getcwd(), "assets"),
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "assets"),
    ]
    seen = []
    for root in roots:
        root = os.path.abspath(root)
        if root not in seen:
            seen.append(root)
    return seen


def first_existing(*names):
    for root in _asset_roots():
        for name in names:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                return path
    return ""


def shade_hex(color, factor):
    text = color.lstrip("#")
    if len(text) != 6:
        return color
    red = max(0, min(255, int(int(text[0:2], 16) * factor)))
    green = max(0, min(255, int(int(text[2:4], 16) * factor)))
    blue = max(0, min(255, int(int(text[4:6], 16) * factor)))
    return f"#{red:02x}{green:02x}{blue:02x}"


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


TITLE_FONT = QFont("Segoe UI", 18)
TITLE_FONT.setWeight(QFont.DemiBold)
SEASON_FONT = QFont("Segoe UI", 14)
SEASON_FONT.setWeight(QFont.DemiBold)


class QtAppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = settings_mod.load_settings()
        self.settings["vlc_path"] = find_vlc(self.settings.get("vlc_path", ""))
        default_count = max(1, int(self.settings.get("default_episode_count") or self.settings.get("universal_count") or 3))
        self.settings["default_episode_count"] = default_count
        self.settings["universal_count"] = default_count
        self.settings["episode_mode"] = "universal"
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
        self.stage.setObjectName("stage")
        self.setCentralWidget(self.stage)
        self.backdrop = Backdrop(self.stage)
        self.glass = QWidget(self.stage)
        self.glass.setObjectName("glass")

        self.installEventFilter(self)
        self._build_menu()
        self._build_glass()
        self._apply_theme()
        self.refresh_library()
        if not self._has_library():
            QTimer.singleShot(250, self.prompt_library)
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
        file_menu.addAction("Add TV library folder…", self.add_library)
        file_menu.addAction("Add movie library folder…", self.add_movie_library)
        file_menu.addAction("Remove a library folder…", self.remove_library)
        file_menu.addAction("Clear all libraries…", self.clear_libraries)
        file_menu.addAction("Rescan library", self.refresh_library)
        file_menu.addSeparator()
        file_menu.addAction(
            "Default number of episodes to queue…",
            self.set_default_episode_count,
        )
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
        shell = QVBoxLayout(self.glass)
        shell.setContentsMargins(12, 10, 12, 8)
        shell.setSpacing(6)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setAutoFillBackground(False)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        shell.addWidget(self.tabs)

        builder = QWidget()
        builder.setObjectName("builderPage")
        builder.setAttribute(Qt.WA_StyledBackground, False)
        builder.setAutoFillBackground(False)
        root = QVBoxLayout(builder)
        root.setContentsMargins(8, 8, 8, 4)
        root.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search shows")
        self.search.textChanged.connect(self.redraw_shows)
        root.addWidget(self.search)

        lists = QHBoxLayout()
        lists.setSpacing(-28)
        left = QVBoxLayout()
        source_row = QHBoxLayout()
        source_row.setContentsMargins(0, 0, 0, 0)
        self.shows_tab = QLabel("Shows")
        self.shows_tab.setObjectName("sourceTabActive")
        self.shows_tab.setFont(TITLE_FONT)
        self.shows_tab.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.shows_tab.mousePressEvent = lambda event: self.set_source("shows")
        self.movies_tab = QLabel("Movies")
        self.movies_tab.setObjectName("sourceTabIdle")
        self.movies_tab.setFont(TITLE_FONT)
        self.movies_tab.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.movies_tab.mousePressEvent = lambda event: self.set_source("movies")
        source_row.addWidget(self.shows_tab, 1)
        source_row.addWidget(self.movies_tab, 1)
        left.addLayout(source_row)
        self.source = "shows"
        self.show_list = QListWidget()
        self.show_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.show_list.setTextElideMode(Qt.ElideRight)
        self.show_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.show_list.itemSelectionChanged.connect(self.redraw_seasons)
        self.show_list.itemDoubleClicked.connect(lambda *_: self.add_selected())
        left.addWidget(self.show_list)
        self.seasons_title = QLabel("Seasons")
        self.seasons_title.setObjectName("sectionTitleLeft")
        self.seasons_title.setFont(SEASON_FONT)
        self.seasons_title.setAlignment(Qt.AlignLeft)
        left.addWidget(self.seasons_title)
        self.season_list = QListWidget()
        self.season_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.season_list.setMaximumHeight(120)
        left.addWidget(self.season_list)
        lists.addLayout(left, 1)

        self.center = QWidget()
        self.center.setObjectName("centerStage")
        self.center.setMinimumWidth(180)
        self.center.setMaximumWidth(790)
        self.center_art = QLabel(self.center)
        self.center_art.setAlignment(Qt.AlignCenter)
        self.center_art.setObjectName("centerArt")
        self.center_art.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        mid = QVBoxLayout(self.center)
        mid.setContentsMargins(8, 8, 8, 8)
        mid.addStretch()
        self.mid_buttons = []
        for text, fn in (
            ("Add →", self.add_selected),
            ("← Remove", self.remove_selected),
            ("Move up", lambda: self.move(-1)),
            ("Move down", lambda: self.move(1)),
            ("Clear", self.clear_order),
        ):
            button = QPushButton(text)
            button.setObjectName("ghost")
            button.clicked.connect(fn)
            mid.addWidget(button)
            self.mid_buttons.append(button)
        mid.addStretch()
        lists.setSpacing(8)
        lists.addWidget(self.center, 0)

        right = QVBoxLayout()
        order_title = QLabel("Watch order")
        order_title.setObjectName("sectionTitle")
        order_title.setFont(TITLE_FONT)
        order_title.setAlignment(Qt.AlignHCenter)
        right.addWidget(order_title)
        self.order_list = QListWidget()
        self.order_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.order_list.setTextElideMode(Qt.ElideRight)
        self.order_list.itemSelectionChanged.connect(self._load_count_for_selection)
        right.addWidget(self.order_list)
        self.now_panel = QWidget()
        self.now_panel.setObjectName("compactPanel")
        now_box = QVBoxLayout(self.now_panel)
        now_box.setContentsMargins(10, 8, 10, 8)
        self.now_label = QLabel("Now playing: —")
        self.next_label = QLabel("Next: —")
        now_box.addWidget(self.now_label)
        now_box.addWidget(self.next_label)
        right.addWidget(self.now_panel)
        lists.addLayout(right, 1)
        root.addLayout(lists, 1)

        options = QHBoxLayout()
        self.count_panel = QWidget()
        self.count_panel.setObjectName("compactPanel")
        self.count_panel.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        count_box = QVBoxLayout(self.count_panel)
        count_box.setContentsMargins(10, 8, 10, 8)
        count_box.addWidget(QLabel("Episodes per show"))
        self.count = QLineEdit(str(self.settings.get("universal_count", 3)))
        self.count.setMaximumWidth(60)
        self.count.editingFinished.connect(self._save_count)
        count_box.addWidget(self.count)
        self.count_all = QRadioButton("All shows")
        self.count_one = QRadioButton("Selected show")
        count_mode = QButtonGroup(self)
        count_mode.addButton(self.count_all)
        count_mode.addButton(self.count_one)
        if self.settings.get("episode_mode") == "individual":
            self.count_one.setChecked(True)
        else:
            self.count_all.setChecked(True)
        self.count_all.toggled.connect(self._save_count)
        count_box.addWidget(self.count_all)
        count_box.addWidget(self.count_one)
        options.addWidget(self.count_panel)

        self.start_panel = QWidget()
        self.start_panel.setObjectName("compactPanel")
        self.start_panel.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        start_box = QVBoxLayout(self.start_panel)
        start_box.setContentsMargins(10, 8, 10, 8)
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
        options.addWidget(self.start_panel)
        options.addStretch()
        root.addLayout(options)

        sleep = QHBoxLayout()
        self.timer_label = QLabel("Sleep timer: off")
        sleep.addWidget(self.timer_label)
        off = QPushButton("Off")
        off.clicked.connect(lambda: self.set_sleep("off"))
        sleep.addWidget(off)
        thirty = QPushButton("30m")
        thirty.clicked.connect(lambda: self.set_sleep("minutes", 30))
        sleep.addWidget(thirty)
        one_h = QPushButton("1h")
        one_h.clicked.connect(lambda: self.set_sleep("minutes", 60))
        sleep.addWidget(one_h)
        saved_min = int(self.settings.get("sleep_timer_minutes", 60))
        hours_default = saved_min / 60 if saved_min >= 60 else 2
        if hours_default == int(hours_default):
            hours_default = str(int(hours_default))
        else:
            hours_default = str(hours_default)
        self.custom_sleep = QLineEdit()
        self.custom_sleep.setMaximumWidth(56)
        self.custom_sleep.setPlaceholderText("Hours")
        self.custom_sleep.editingFinished.connect(self.apply_custom_sleep)
        sleep.addWidget(self.custom_sleep)
        sleep.addStretch()
        play = QPushButton("Start playback")
        play.setObjectName("accent")
        play.clicked.connect(self.start)
        sleep.addWidget(play)
        root.addLayout(sleep)
        self.status = QLabel("Ready.")
        root.addWidget(self.status)

        self.tabs.addTab(builder, "Builder Screen")

        history_page = QWidget()
        history_page.setObjectName("historyPage")
        history_page.setAttribute(Qt.WA_StyledBackground, False)
        history_page.setAutoFillBackground(False)
        history_layout = QVBoxLayout(history_page)
        history_layout.setContentsMargins(8, 8, 8, 8)
        hint = QLabel("Last 500 files played.")
        hint.setObjectName("muted")
        history_layout.addWidget(hint)
        self.history_view = QPlainTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setObjectName("historyLog")
        history_layout.addWidget(self.history_view)
        self.tabs.addTab(history_page, "History")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and hasattr(self, "custom_sleep"):
            focused = QApplication.focusWidget()
            if focused is self.custom_sleep:
                target = QApplication.widgetAt(event.globalPosition().toPoint())
                if target is not self.custom_sleep:
                    self.custom_sleep.clearFocus()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_layers()

    def _layout_layers(self):
        area = self.stage.rect()
        self.backdrop.setGeometry(area)
        margin = 12
        self.glass.setGeometry(
            margin,
            margin,
            max(1, area.width() - margin * 2),
            max(1, area.height() - margin * 2),
        )
        self.backdrop.lower()
        self.glass.raise_()
        self._scale_center_art()

    def _scale_center_art(self):
        pix = getattr(self, "_center_pixmap", None)
        if pix is None or pix.isNull() or THEMES[self.theme_name]["glass"] is False:
            self.center_art.hide()
            return
        host = self.glass
        box = host.size()
        if box.height() < 10:
            return
        self.center_art.setParent(host)
        # Fill the window height. Width follows aspect ratio (~790 if the PNG is 790 wide).
        scaled = pix.scaledToHeight(box.height(), Qt.SmoothTransformation)
        self.center_art.setPixmap(scaled)
        self.center_art.resize(scaled.size())
        x = (box.width() - scaled.width()) // 2
        self.center_art.move(max(0, x), 0)
        self.center_art.show()
        self.center_art.lower()

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
                first_existing("waifu_bg_placeholder.png"),
                "",
            )
            self.backdrop.show()
            char = first_existing("12-26-23-chaesu.png")
            if char:
                pix = QPixmap(char)
                self._center_pixmap = pix
                self._scale_center_art()
            else:
                self._center_pixmap = None
                self.center_art.clear()
            self.center_art.show()
        else:
            self.backdrop.set_art("", "")
            self.backdrop.hide()
            self.center_art.clear()
            self.center_art.hide()
        tab_idle = shade_hex(colors['accent'], 0.38)
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget#stage {{ background: {colors['bg']}; color: {colors['fg']}; }}
            QWidget {{ color: {colors['fg']}; }}
            QMenuBar, QMenu {{ background: {colors['bg']}; color: {colors['fg']}; }}
            #glass {{
                background-color: {colors['panel']};
                border-radius: 14px;
            }}
            QTabWidget#mainTabs, QTabWidget#mainTabs::pane,
            QTabWidget#mainTabs QStackedWidget,
            QTabBar, #builderPage, #historyPage {{
                background: transparent;
                border: none;
            }}
            QTabWidget#mainTabs::pane {{
                top: 0px;
                border: none;
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
            QPushButton#ghost {{
                background: rgba(28, 28, 30, 128);
                color: {colors['fg']};
            }}
            #centerArt {{ background: transparent; }}
            #centerStage {{ background: transparent; }}
            #midOverlay {{ background: transparent; }}
            #compactPanel {{
                background: {colors['panel']};
                border-radius: 8px;
            }}
            QPushButton#accent {{
                background: {colors['accent']};
                color: {colors['accent_fg']};
                padding: 10px 18px;
            }}
            QLabel#title {{ font-size: 22px; font-weight: 700; background: transparent; }}
            QLabel#sectionTitle {{
                background: transparent;
                font-size: 18px;
                font-weight: 600;
                padding: 4px 0 6px 0;
            }}
            QLabel#sectionTitleLeft {{
                background: transparent;
                font-size: 14px;
                font-weight: 600;
                padding: 2px 0 4px 0;
            }}

            QLabel#muted {{ color: {colors['muted']}; }}
            QTabWidget#mainTabs::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {tab_idle};
                color: {colors['fg']};
                padding: 8px 18px;
                margin-right: 4px;
                border: none;
                border-radius: 6px 6px 0 0;
            }}
            QTabBar::tab:selected {{
                background: {colors['accent']};
                color: {colors['accent_fg']};
            }}
            QPlainTextEdit#historyLog {{
                background: {colors['field']};
                color: {colors['fg']};
                border: none;
                font-family: Consolas, "Segoe UI", sans-serif;
            }}

            QScrollBar:vertical {{
                background: rgba(255, 255, 255, 36);
                width: 10px;
                margin: 0px;
                border: none;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors['accent']};
                min-height: 32px;
                border: none;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:vertical:pressed {{
                background: {colors['fg']};
                border: none;
                border-radius: 5px;
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
                background: rgba(255, 255, 255, 36);
                height: 10px;
                margin: 0px;
                border: none;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {colors['accent']};
                min-width: 32px;
                border: none;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover,
            QScrollBar::handle:horizontal:pressed {{
                background: {colors['fg']};
                border: none;
                border-radius: 5px;
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
            QLabel#title {{ font-size: 22px; font-weight: 700; background: transparent; }}
            QLabel#sectionTitle {{
                background: transparent;
                font-size: 18px;
                font-weight: 600;
                padding: 4px 0 6px 0;
            }}
            QLabel#sectionTitleLeft {{
                background: transparent;
                font-size: 14px;
                font-weight: 600;
                padding: 2px 0 4px 0;
            }}

            QLabel#muted {{ color: {colors['muted']}; }}
            QTabWidget#mainTabs::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: {tab_idle};
                color: {colors['fg']};
                padding: 8px 18px;
                margin-right: 4px;
                border: none;
                border-radius: 6px 6px 0 0;
            }}
            QTabBar::tab:selected {{
                background: {colors['accent']};
                color: {colors['accent_fg']};
            }}
            QPlainTextEdit#historyLog {{
                background: {colors['field']};
                color: {colors['fg']};
                border: none;
                font-family: Consolas, "Segoe UI", sans-serif;
            }}

            """
        )
        self._refresh_timer_label()
        self._layout_layers()

    def _selected_order_entry(self):
        item = self.order_list.currentItem()
        return item.text() if item else None

    def _load_count_for_selection(self):
        if not self.count_one.isChecked():
            self.count.setText(str(self.settings.get("universal_count", 3)))
            return
        entry = self._selected_order_entry()
        individual = self.settings.setdefault("individual_counts", {})
        if entry and entry in individual:
            self.count.setText(str(individual[entry]))
        elif entry:
            show = entry.split(" — ")[0]
            self.count.setText(str(individual.get(show, self.settings.get("universal_count", 3))))
        else:
            self.count.setText(str(self.settings.get("universal_count", 3)))

    def _save_count(self, *_):
        try:
            value = max(1, int(self.count.text()))
        except ValueError:
            return
        if self.count_one.isChecked():
            self.settings["episode_mode"] = "individual"
            entry = self._selected_order_entry()
            if entry:
                self.settings.setdefault("individual_counts", {})[entry] = value
        else:
            self.settings["episode_mode"] = "universal"
            self.settings["universal_count"] = value
        self.persist()

    def set_default_episode_count(self):
        current = max(1, int(self.settings.get("default_episode_count", 3)))
        value, ok = QInputDialog.getInt(
            self,
            "Default episodes to queue",
            "Used for every show when All shows is selected.\n"
            "Applied again the next time Witching Hour starts.",
            current,
            1,
            99,
            1,
        )
        if not ok:
            return
        self.settings["default_episode_count"] = value
        self.settings["universal_count"] = value
        self.settings["episode_mode"] = "universal"
        self.count.setText(str(value))
        self.count_all.setChecked(True)
        self.persist()
        self.status.setText(f"Default episodes to queue is now {value}.")

    def _on_tab_changed(self, index):
        if index == 1:
            self.refresh_history()

    def refresh_history(self):
        entries = list(reversed(self.memory.load_history(500)))
        lines = []
        for item in entries:
            when = item.get("when", "")
            show = item.get("show", "")
            try:
                season = int(item.get("season") or 0)
                episode = int(item.get("episode") or 0)
                stamp = f"S{season:02d}E{episode:02d}"
            except (TypeError, ValueError):
                stamp = ""
            path = item.get("path", "")
            name = os.path.basename(path) if path else ""
            lines.append(f"{when}  {show}  {stamp}  {name}".rstrip())
        self.history_view.setPlainText("\n".join(lines) if lines else "Nothing played yet.")

    def persist(self):
        try:
            value = max(1, int(self.count.text()))
        except ValueError:
            value = int(self.settings.get("universal_count", 3))
        if hasattr(self, "count_one") and self.count_one.isChecked():
            self.settings["episode_mode"] = "individual"
            entry = self._selected_order_entry()
            if entry:
                self.settings.setdefault("individual_counts", {})[entry] = value
        else:
            self.settings["episode_mode"] = "universal"
            self.settings["universal_count"] = value
        self.settings["start_mode"] = "random" if self.start_random.isChecked() else "memory"
        settings_mod.save_settings(self.settings)

    def set_source(self, source):
        self.source = "movies" if source == "movies" else "shows"
        if self.source == "movies":
            self.shows_tab.setObjectName("sourceTabIdle")
            self.movies_tab.setObjectName("sourceTabActive")
            self.seasons_title.hide()
            self.season_list.hide()
        else:
            self.shows_tab.setObjectName("sourceTabActive")
            self.movies_tab.setObjectName("sourceTabIdle")
            self.seasons_title.show()
            self.season_list.show()
        self.shows_tab.style().unpolish(self.shows_tab)
        self.shows_tab.style().polish(self.shows_tab)
        self.movies_tab.style().unpolish(self.movies_tab)
        self.movies_tab.style().polish(self.movies_tab)
        self.redraw_shows()

    def refresh_library(self):
        self.library.scan(
            self.settings.get("library_folders", []),
            self.settings.get("movie_folders", []),
        )
        kept = []
        for entry in self.settings.get("watch_order", []):
            show, _season = parse_watch_entry(entry)
            if show in self.library.paths:
                kept.append(entry)
        self.settings["watch_order"] = kept
        self.redraw_shows()
        self.redraw_order()
        self.status.setText(
            f"{len(self.library.shows)} shows, {len(self.library.movies)} movies"
        )
        self.persist()

    def redraw_shows(self):
        query = self.search.text().strip().lower()
        pool = self.library.movies if self.source == "movies" else self.library.shows
        if query:
            self.filtered = [show for show in pool if query in show.lower()]
        else:
            self.filtered = list(pool)
        self.show_list.clear()
        self.show_list.addItems(self.filtered)
        self.redraw_seasons()

    def redraw_seasons(self):
        self.season_list.clear()
        self.season_list.addItem("All seasons")
        if self.source == "movies":
            return
        items = self.show_list.selectedItems()
        if len(items) != 1:
            self.season_list.setCurrentRow(0)
            return
        show = items[0].text()
        if self.library.kinds.get(show) == "movie":
            return
        for number in self.library.seasons_for(show):
            self.season_list.addItem(f"Season {number:02d}")
        self.season_list.setCurrentRow(0)

    def redraw_order(self):
        self.order_list.clear()
        self.order_list.addItems(self.settings.get("watch_order", []))

    def selected_season(self):
        if self.source == "movies":
            return None
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

    def _has_library(self):
        folders = self.settings.get("library_folders") or []
        return any(isinstance(folder, str) and os.path.isdir(folder) for folder in folders)

    def prompt_library(self):
        box = QMessageBox(self)
        box.setWindowTitle("Choose a library")
        box.setText(
            "Witching Hour needs a folder of shows before it can build a playlist.\n\n"
            "Pick the directory that contains your series folders "
            "(for example a 'TV Shows' folder)."
        )
        choose = box.addButton("Choose folder…", QMessageBox.AcceptRole)
        box.addButton("Later", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() == choose:
            self.add_library()
        if not self._has_library():
            self.status.setText("No library yet. File → Add library folder when you are ready.")

    def add_library(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a TV library folder")
        if not folder:
            return
        folder = os.path.normpath(folder)
        folders = self.settings.setdefault("library_folders", [])
        if folder not in folders:
            folders.append(folder)
        self.refresh_library()

    def add_movie_library(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a movie library folder")
        if not folder:
            return
        folder = os.path.normpath(folder)
        folders = self.settings.setdefault("movie_folders", [])
        if folder not in folders:
            folders.append(folder)
        self.refresh_library()
        self.set_source("movies")

    def remove_library(self):
        tv = list(self.settings.get("library_folders", []))
        movies = list(self.settings.get("movie_folders", []))
        labels = [f"TV: {path}" for path in tv] + [f"Movie: {path}" for path in movies]
        if not labels:
            self.status.setText("No library folders to remove.")
            return
        choice, ok = QInputDialog.getItem(
            self, "Remove library folder", "Folder", labels, 0, False
        )
        if not ok:
            return
        path = choice.split(": ", 1)[-1]
        self.settings["library_folders"] = [item for item in tv if item != path]
        self.settings["movie_folders"] = [item for item in movies if item != path]
        self.refresh_library()

    def clear_libraries(self):
        if not self.settings.get("library_folders") and not self.settings.get("movie_folders"):
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
        self.settings["movie_folders"] = []
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
        raw = self.custom_sleep.text().strip().lower().replace("h", "")
        if not raw:
            return
        try:
            hours = float(raw)
            if hours <= 0 or hours > 24:
                raise ValueError
        except ValueError:
            self.status.setText("Enter hours between 0.5 and 24.")
            return
        minutes = max(1, int(round(hours * 60)))
        self.set_sleep("minutes", minutes)

    def set_sleep(self, mode, minutes=None):
        self.settings["sleep_timer_mode"] = mode
        if minutes is not None:
            self.settings["sleep_timer_minutes"] = int(minutes)
        self.persist()
        self._refresh_timer_label()
        if self.vlc.running():
            self._arm_sleep_timer()

    def _refresh_timer_label(self):
        mode = self.settings.get("sleep_timer_mode", "off")
        if mode == "off":
            self.timer_label.setText("Sleep timer: off")
            return
        minutes = int(self.settings.get("sleep_timer_minutes", 60))
        if minutes % 60 == 0:
            hours = minutes // 60
            label = f"{hours}h" if hours != 1 else "1h"
        else:
            label = f"{minutes}m"
        self.timer_label.setText(f"Sleep timer: {label}")

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
        self.memory.record_play(items[0])
        self._update_now(0)
        self.status.setText(f"Playing {len(items)} episode(s)")
        self.monitor.start()
        QTimer.singleShot(1500, self._arm_sleep_timer)

    def _update_now(self, index):
        items = self.memory.session.get("items", [])
        if not items or index >= len(items):
            return
        item = items[index]
        self.memory.record_play(item)
        if hasattr(self, "tabs") and self.tabs.currentIndex() == 1:
            self.refresh_history()
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
                    if candidate != index:
                        if candidate > index:
                            for done in items[index:candidate]:
                                self.memory.advance(done)
                            for seen in items[index:candidate + 1]:
                                self.memory.record_play(seen)
                        else:
                            self.memory.record_play(item)
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
            self.memory.record_play(items[index])
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