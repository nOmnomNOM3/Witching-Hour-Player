import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import os
import sys
import re
import random
import subprocess
import json
import socket
import time
from datetime import datetime
from urllib.parse import urlparse, unquote


# ============================================================
# WITCHING HOUR
# ============================================================


# ============================================================
# PROGRAM FOLDER
# Works correctly as both .py and PyInstaller .exe
# ============================================================

if getattr(sys, "frozen", False):
    program_folder = os.path.dirname(sys.executable)
else:
    program_folder = os.path.dirname(os.path.abspath(__file__))


settings_file = os.path.join(
    program_folder,
    "witching_hour_settings.json"
)

memory_file = os.path.join(
    program_folder,
    "playback_memory.json"
)

history_file = os.path.join(
    program_folder,
    "watch_history.json"
)

lineups_file = os.path.join(
    program_folder,
    "saved_lineups.json"
)

unfinished_session_file = os.path.join(
    program_folder,
    "unfinished_session.json"
)

legacy_library_file = os.path.join(
    program_folder,
    "library_folders.json"
)


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_SETTINGS = {
    "vlc_path": r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    "library_folders": [],
    "watch_order": [],
    "episode_mode": "universal",
    "universal_count": 3,
    "individual_counts": {},
    "start_mode": "memory",
    "history_limit": 100,
    "sleep_timer_mode": "off",
    "sleep_timer_minutes": 60
}


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(path, default):

    if not os.path.exists(path):
        return default

    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
        TypeError
    ):
        return default


def save_json(path, data):

    try:
        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    except OSError:
        pass


def delete_json_file(path):

    try:
        if os.path.exists(path):
            os.remove(path)

    except OSError:
        pass


# ============================================================
# SETTINGS
# ============================================================

settings = load_json(
    settings_file,
    DEFAULT_SETTINGS.copy()
)

for key, value in DEFAULT_SETTINGS.items():

    if key not in settings:
        settings[key] = value


# ------------------------------------------------------------
# MIGRATE OLD LIBRARY SETTINGS
# ------------------------------------------------------------

if (
    not settings["library_folders"]
    and os.path.exists(legacy_library_file)
):

    old_folders = load_json(
        legacy_library_file,
        []
    )

    if isinstance(old_folders, list):

        settings["library_folders"] = [
            folder
            for folder in old_folders
            if isinstance(folder, str)
        ]


vlc_path = settings["vlc_path"]
library_folders = settings["library_folders"]
watch_order = settings["watch_order"]
episode_mode = settings["episode_mode"]
individual_counts = settings["individual_counts"]
start_mode = settings["start_mode"]
history_limit = settings["history_limit"]
sleep_timer_mode = settings["sleep_timer_mode"]
sleep_timer_minutes = settings["sleep_timer_minutes"]


def save_settings():

    settings["vlc_path"] = vlc_path
    settings["library_folders"] = library_folders
    settings["watch_order"] = watch_order
    settings["episode_mode"] = episode_mode
    settings["individual_counts"] = individual_counts
    settings["start_mode"] = start_mode
    settings["history_limit"] = history_limit
    settings["sleep_timer_mode"] = sleep_timer_mode
    settings["sleep_timer_minutes"] = sleep_timer_minutes

    try:
        settings["universal_count"] = int(
            episode_entry.get()
        )

    except Exception:
        pass

    save_json(
        settings_file,
        settings
    )


# ============================================================
# PLAYBACK MEMORY
#
# Example:
#
# "Batman": {
#     "season": 1,
#     "episode": 7,
#     "resume_time": 742,
#     "path": "D:\\Videos\\..."
# }
#
# resume_time = 0 means start normally.
# ============================================================

playback_memory = load_json(
    memory_file,
    {}
)

if not isinstance(playback_memory, dict):
    playback_memory = {}


def save_memory():

    save_json(
        memory_file,
        playback_memory
    )


def set_episode_memory(
    show,
    season,
    episode,
    resume_time=0,
    path=None
):

    playback_memory[show] = {
        "season": int(season),
        "episode": int(episode),
        "resume_time": max(
            0,
            int(resume_time)
        )
    }

    if path:
        playback_memory[show]["path"] = path

    save_memory()


def advance_memory_for_item(item):

    show = item.get("show")

    if not show:
        return

    next_season = item.get(
        "next_season"
    )

    next_episode = item.get(
        "next_episode"
    )

    if (
        next_season is None
        or next_episode is None
    ):
        return

    set_episode_memory(
        show,
        next_season,
        next_episode,
        0
    )


def save_interruption_memory(
    item,
    seconds
):

    show = item.get("show")

    if not show:
        return

    set_episode_memory(
        show,
        item.get(
            "season",
            1
        ),
        item.get(
            "episode",
            1
        ),
        max(
            0,
            int(seconds)
        ),
        item.get("path")
    )


# ============================================================
# HISTORY
# ============================================================

watch_history = load_json(
    history_file,
    []
)

if not isinstance(watch_history, list):
    watch_history = []


def save_history():

    global watch_history

    watch_history = watch_history[
        -history_limit:
    ]

    save_json(
        history_file,
        watch_history
    )


# ============================================================
# SAVED LINEUPS
# ============================================================

saved_lineups = load_json(
    lineups_file,
    {}
)

if not isinstance(saved_lineups, dict):
    saved_lineups = {}


def save_lineups():

    save_json(
        lineups_file,
        saved_lineups
    )


# ============================================================
# UNFINISHED PLAYBACK SESSION
# ============================================================

unfinished_session = load_json(
    unfinished_session_file,
    {}
)

if not isinstance(unfinished_session, dict):
    unfinished_session = {}


def save_unfinished_session():

    if not unfinished_session:
        delete_json_file(
            unfinished_session_file
        )
        return

    save_json(
        unfinished_session_file,
        unfinished_session
    )


def clear_unfinished_session():

    global unfinished_session

    unfinished_session = {}

    delete_json_file(
        unfinished_session_file
    )


def has_valid_unfinished_session():

    if not unfinished_session:
        return False

    items = unfinished_session.get(
        "items",
        []
    )

    if not isinstance(items, list):
        return False

    if not items:
        return False

    current_index = unfinished_session.get(
        "current_index",
        0
    )

    if not isinstance(current_index, int):
        return False

    if current_index < 0:
        return False

    if current_index >= len(items):
        return False

    # Current item must still exist.
    current_path = items[
        current_index
    ].get(
        "path"
    )

    if not current_path:
        return False

    if not os.path.exists(
        current_path
    ):
        return False

    return True


# ============================================================
# SHOW LIBRARY
# ============================================================

shows = []
filtered_shows = []
show_paths = {}


def scan_library():

    global shows
    global show_paths

    shows = []
    show_paths = {}

    for library_folder in library_folders:

        if not os.path.isdir(
            library_folder
        ):
            continue

        try:
            items = os.listdir(
                library_folder
            )

        except OSError:
            continue

        for item in items:

            item_path = os.path.join(
                library_folder,
                item
            )

            if not os.path.isdir(
                item_path
            ):
                continue

            display_name = item

            if display_name in show_paths:

                parent_name = os.path.basename(
                    library_folder
                )

                display_name = (
                    f"{item} [{parent_name}]"
                )

                original_name = display_name

                counter = 2

                while display_name in show_paths:

                    display_name = (
                        f"{original_name} {counter}"
                    )

                    counter += 1

            show_paths[
                display_name
            ] = item_path

            shows.append(
                display_name
            )

    shows.sort(
        key=str.lower
    )


# ============================================================
# EPISODE SCANNER
# ============================================================

def find_episodes(show_folder):

    episodes = []

    ignored_folders = {
        "extras",
        "extra",
        "movies",
        "movie",
        "special features",
        "behind the scenes",
        "bonus",
        "bonus features",
        "trailers"
    }

    for root, folders, files in os.walk(
        show_folder
    ):

        folders[:] = [
            folder
            for folder in folders
            if folder.lower()
            not in ignored_folders
        ]

        folder_name = os.path.basename(
            root
        )

        folder_season = None

        season_match = re.search(
            r"(?:Season|S)\s*[-.]?\s*(\d+)",
            folder_name,
            re.IGNORECASE
        )

        if season_match:

            folder_season = int(
                season_match.group(1)
            )

        else:

            folder_match = re.match(
                r"^\s*(\d+)\s*-\s*\d+",
                folder_name
            )

            if folder_match:

                folder_season = int(
                    folder_match.group(1)
                )

        for filename in files:

            if not filename.lower().endswith(
                (
                    ".mkv",
                    ".mp4",
                    ".avi",
                    ".mov"
                )
            ):
                continue

            season_number = None
            episode_number = None

            match = re.search(
                r"\bS\s*(\d+)\s*[-.]?\s*E\s*(\d+)\b",
                filename,
                re.IGNORECASE
            )

            if match:

                season_number = int(
                    match.group(1)
                )

                episode_number = int(
                    match.group(2)
                )

            else:

                match = re.search(
                    r"\bSeason\s*(\d+)\s+Episode\s*(\d+)\b",
                    filename,
                    re.IGNORECASE
                )

                if match:

                    season_number = int(
                        match.group(1)
                    )

                    episode_number = int(
                        match.group(2)
                    )

                else:

                    match = re.search(
                        r"\bEpisode\s*(\d+)\b",
                        filename,
                        re.IGNORECASE
                    )

                    if match:

                        episode_number = int(
                            match.group(1)
                        )

                        season_number = (
                            folder_season
                            if folder_season is not None
                            else 1
                        )

                    else:

                        match = re.search(
                            r"\bEp\.?\s*(\d+)\b",
                            filename,
                            re.IGNORECASE
                        )

                        if match:

                            episode_number = int(
                                match.group(1)
                            )

                            season_number = (
                                folder_season
                                if folder_season is not None
                                else 1
                            )

                        else:

                            match = re.search(
                                r"\bE(\d+)\b",
                                filename,
                                re.IGNORECASE
                            )

                            if match:

                                episode_number = int(
                                    match.group(1)
                                )

                                season_number = (
                                    folder_season
                                    if folder_season is not None
                                    else 1
                                )

                            else:

                                match = re.search(
                                    r"\b(\d+)\s*-\s*(\d+)\b",
                                    filename
                                )

                                if match:

                                    season_number = int(
                                        match.group(1)
                                    )

                                    episode_number = int(
                                        match.group(2)
                                    )

                                else:

                                    match = re.search(
                                        r"-\s*(\d{1,3})\s*-",
                                        filename
                                    )

                                    if match:

                                        episode_number = int(
                                            match.group(1)
                                        )

                                        season_number = (
                                            folder_season
                                            if folder_season is not None
                                            else 1
                                        )

                                    else:

                                        match = re.search(
                                            r"-\s*(\d{1,3})(?:\s*\[|\s*$)",
                                            filename
                                        )

                                        if match:

                                            episode_number = int(
                                                match.group(1)
                                            )

                                            season_number = (
                                                folder_season
                                                if folder_season is not None
                                                else 1
                                            )

                                        else:

                                            match = re.search(
                                                r"\.(\d{1,3})\.",
                                                filename
                                            )

                                            if match:

                                                episode_number = int(
                                                    match.group(1)
                                                )

                                                season_number = (
                                                    folder_season
                                                    if folder_season is not None
                                                    else 1
                                                )

                                            else:

                                                match = re.search(
                                                    r"_(\d+)(?:\D|$)",
                                                    filename
                                                )

                                                if match:

                                                    episode_number = int(
                                                        match.group(1)
                                                    )

                                                    season_number = (
                                                        folder_season
                                                        if folder_season is not None
                                                        else 1
                                                    )

            if (
                season_number is not None
                and episode_number is not None
            ):

                episodes.append(
                    (
                        season_number,
                        episode_number,
                        os.path.join(
                            root,
                            filename
                        )
                    )
                )

    episodes.sort(
        key=lambda x: (
            x[0],
            x[1]
        )
    )

    # --------------------------------------------------------
    # FALLBACK FOR UNNUMBERED SHOWS
    # --------------------------------------------------------

    if not episodes:

        unnumbered_files = []

        for root, folders, files in os.walk(
            show_folder
        ):

            folders[:] = [
                folder
                for folder in folders
                if folder.lower()
                not in ignored_folders
            ]

            for filename in files:

                if filename.lower().endswith(
                    (
                        ".mkv",
                        ".mp4",
                        ".avi",
                        ".mov"
                    )
                ):

                    unnumbered_files.append(
                        os.path.join(
                            root,
                            filename
                        )
                    )

        unnumbered_files.sort(
            key=lambda path:
            os.path.basename(
                path
            ).lower()
        )

        for index, filepath in enumerate(
            unnumbered_files,
            start=1
        ):

            episodes.append(
                (
                    1,
                    index,
                    filepath
                )
            )

    return episodes


# ============================================================
# STARTING EPISODE
# ============================================================

def get_starting_index(
    show,
    episodes
):

    if start_mode == "random":

        return random.randint(
            0,
            len(episodes) - 1
        )

    memory = playback_memory.get(
        show
    )

    if not isinstance(memory, dict):

        return random.randint(
            0,
            len(episodes) - 1
        )

    saved_season = memory.get(
        "season"
    )

    saved_episode = memory.get(
        "episode"
    )

    if (
        saved_season is None
        or saved_episode is None
    ):

        return random.randint(
            0,
            len(episodes) - 1
        )

    for index, episode in enumerate(
        episodes
    ):

        if (
            episode[0] == saved_season
            and episode[1] == saved_episode
        ):

            return index

    return 0


def get_resume_time_for_episode(
    show,
    episode
):

    if start_mode != "memory":
        return 0

    memory = playback_memory.get(
        show
    )

    if not isinstance(memory, dict):
        return 0

    if (
        memory.get("season") == episode[0]
        and memory.get("episode") == episode[1]
    ):

        try:
            return max(
                0,
                int(
                    memory.get(
                        "resume_time",
                        0
                    )
                )
            )

        except (
            TypeError,
            ValueError
        ):
            return 0

    return 0


# ============================================================
# VLC CONTROL
# ============================================================

current_vlc_process = None
current_vlc_port = None

sleep_timer_after_id = None
end_episode_after_id = None
playback_monitor_after_id = None


def find_free_port():

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    sock.bind(
        (
            "127.0.0.1",
            0
        )
    )

    port = sock.getsockname()[1]

    sock.close()

    return port


def vlc_rc_text(command):

    if not current_vlc_port:
        return None

    try:

        sock = socket.create_connection(
            (
                "127.0.0.1",
                current_vlc_port
            ),
            timeout=0.5
        )

        sock.settimeout(
            0.15
        )

        # Drain greeting/prompt.
        try:
            while True:
                data = sock.recv(
                    4096
                )

                if not data:
                    break

        except socket.timeout:
            pass

        sock.sendall(
            (
                command
                + "\n"
            ).encode(
                "utf-8"
            )
        )

        time.sleep(
            0.04
        )

        response = b""

        try:

            while True:

                chunk = sock.recv(
                    4096
                )

                if not chunk:
                    break

                response += chunk

        except socket.timeout:
            pass

        sock.close()

        return response.decode(
            "utf-8",
            errors="ignore"
        )

    except OSError:
        return None


def vlc_rc_number(command):

    text = vlc_rc_text(
        command
    )

    if not text:
        return None

    # Strip prompts and look for standalone numeric output.
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in reversed(
        lines
    ):

        match = re.fullmatch(
            r"-?\d+",
            line
        )

        if match:

            try:
                return int(
                    match.group(0)
                )

            except ValueError:
                pass

    numbers = re.findall(
        r"(?<![\w.])-?\d+(?![\w.])",
        text
    )

    if not numbers:
        return None

    try:
        return int(
            numbers[-1]
        )

    except ValueError:
        return None


def pause_vlc():

    result = vlc_rc_text(
        "pause"
    )

    if result is not None:

        status_label.config(
            text="Sleep timer paused VLC. 🌙"
        )

        timer_status_label.config(
            text="Sleep Timer: Completed"
        )

    else:

        status_label.config(
            text="Could not reach VLC to pause playback."
        )


# ============================================================
# VLC CURRENT MEDIA DETECTION
# ============================================================

def normalize_media_path(path):

    if not path:
        return ""

    path = path.strip().strip(
        "\"'"
    )

    if path.lower().startswith(
        "file://"
    ):

        parsed = urlparse(
            path
        )

        path = unquote(
            parsed.path
        )

        # Windows file:///D:/...
        if re.match(
            r"^/[A-Za-z]:/",
            path
        ):
            path = path[1:]

        path = path.replace(
            "/",
            os.sep
        )

    try:

        return os.path.normcase(
            os.path.abspath(
                path
            )
        )

    except Exception:

        return os.path.normcase(
            path
        )


def get_current_vlc_path():

    text = vlc_rc_text(
        "status"
    )

    if not text:
        return None

    match = re.search(
        r"new input:\s*(.*?)\s*\)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return normalize_media_path(
        match.group(1)
    )


def find_session_item_index(
    current_path
):

    if not current_path:
        return None

    items = unfinished_session.get(
        "items",
        []
    )

    for index, item in enumerate(
        items
    ):

        item_path = normalize_media_path(
            item.get(
                "path",
                ""
            )
        )

        if item_path == current_path:
            return index

    return None


# ============================================================
# PLAYBACK SESSION MONITOR
# ============================================================

def cancel_playback_monitor():

    global playback_monitor_after_id

    if playback_monitor_after_id is not None:

        try:
            window.after_cancel(
                playback_monitor_after_id
            )

        except Exception:
            pass

    playback_monitor_after_id = None


def mark_items_completed(
    start_index,
    end_index
):

    items = unfinished_session.get(
        "items",
        []
    )

    for index in range(
        start_index,
        end_index
    ):

        if (
            0 <= index
            < len(items)
        ):

            advance_memory_for_item(
                items[index]
            )


def update_now_playing_from_session(
    index
):

    items = unfinished_session.get(
        "items",
        []
    )

    if not items:
        return

    if (
        index < 0
        or index >= len(items)
    ):
        return

    item = items[
        index
    ]

    now_playing_label.config(
        text=(
            f"Now Playing: "
            f"{item.get('show', 'Unknown')} — "
            f"S{int(item.get('season', 1)):02d}"
            f"E{int(item.get('episode', 1)):02d}"
        )
    )

    next_index = index + 1

    if next_index < len(items):

        next_item = items[
            next_index
        ]

        next_up_label.config(
            text=(
                f"Next Up: "
                f"{next_item.get('show', 'Unknown')} — "
                f"S{int(next_item.get('season', 1)):02d}"
                f"E{int(next_item.get('episode', 1)):02d}"
            )
        )

    else:

        next_up_label.config(
            text="Next Up: End of lineup"
        )


def playback_monitor():

    global playback_monitor_after_id

    if not unfinished_session:

        playback_monitor_after_id = None
        return

    items = unfinished_session.get(
        "items",
        []
    )

    if not items:

        clear_unfinished_session()

        playback_monitor_after_id = None
        return

    # --------------------------------------------------------
    # VLC PROCESS CLOSED
    # --------------------------------------------------------

    if (
        current_vlc_process is not None
        and current_vlc_process.poll() is not None
    ):

        # Last successful monitor update is already saved.
        # Keep the session because playback ended early unless
        # it had already been detected as fully complete.

        status_label.config(
            text=(
                "VLC closed. Playback position saved for later. 🌙"
            )
        )

        playback_monitor_after_id = None
        return

    current_path = get_current_vlc_path()

    current_time = vlc_rc_number(
        "get_time"
    )

    current_length = vlc_rc_number(
        "get_length"
    )

    detected_index = find_session_item_index(
        current_path
    )

    old_index = unfinished_session.get(
        "current_index",
        0
    )

    if not isinstance(
        old_index,
        int
    ):
        old_index = 0

    # --------------------------------------------------------
    # DETECT PLAYLIST ADVANCEMENT
    # --------------------------------------------------------

    if detected_index is not None:

        if detected_index > old_index:

            mark_items_completed(
                old_index,
                detected_index
            )

        unfinished_session[
            "current_index"
        ] = detected_index

        old_index = detected_index

    # --------------------------------------------------------
    # SAVE CURRENT TIMESTAMP
    # --------------------------------------------------------

    if (
        current_time is not None
        and 0 <= old_index < len(items)
    ):

        unfinished_session[
            "current_time"
        ] = max(
            0,
            int(current_time)
        )

        unfinished_session[
            "updated"
        ] = datetime.now().isoformat(
            timespec="seconds"
        )

        save_interruption_memory(
            items[old_index],
            current_time
        )

        save_unfinished_session()

        update_now_playing_from_session(
            old_index
        )

    # --------------------------------------------------------
    # DETECT FULL PLAYLIST COMPLETION
    # --------------------------------------------------------

    if (
        old_index == len(items) - 1
        and current_time is not None
        and current_length is not None
        and current_length > 5
        and current_time >= current_length - 2
    ):

        advance_memory_for_item(
            items[old_index]
        )

        clear_unfinished_session()

        now_playing_label.config(
            text="Now Playing: Lineup completed"
        )

        next_up_label.config(
            text="Next Up: —"
        )

        status_label.config(
            text="Playlist completed. Playback memory advanced. 🎃"
        )

        playback_monitor_after_id = None
        return

    playback_monitor_after_id = window.after(
        2000,
        playback_monitor
    )


def begin_playback_monitor():

    cancel_playback_monitor()

    # Give VLC time to start the RC interface.
    global playback_monitor_after_id

    playback_monitor_after_id = window.after(
        1800,
        playback_monitor
    )


# ============================================================
# SLEEP TIMER
# ============================================================

def cancel_sleep_timer():

    global sleep_timer_after_id
    global end_episode_after_id

    if sleep_timer_after_id is not None:

        try:
            window.after_cancel(
                sleep_timer_after_id
            )

        except Exception:
            pass

    if end_episode_after_id is not None:

        try:
            window.after_cancel(
                end_episode_after_id
            )

        except Exception:
            pass

    sleep_timer_after_id = None
    end_episode_after_id = None


def start_sleep_timer():

    global sleep_timer_after_id

    cancel_sleep_timer()

    if sleep_timer_mode == "off":

        timer_status_label.config(
            text="Sleep Timer: Off"
        )

        return

    if sleep_timer_mode == "end_episode":

        timer_status_label.config(
            text="Sleep Timer: End of current episode"
        )

        poll_end_of_episode()

        return

    milliseconds = int(
        sleep_timer_minutes
        * 60
        * 1000
    )

    sleep_timer_after_id = window.after(
        milliseconds,
        pause_vlc
    )

    timer_status_label.config(
        text=f"Sleep Timer: {sleep_timer_minutes} min"
    )


def poll_end_of_episode():

    global end_episode_after_id

    if sleep_timer_mode != "end_episode":
        return

    current_time = vlc_rc_number(
        "get_time"
    )

    total_length = vlc_rc_number(
        "get_length"
    )

    if (
        current_time is not None
        and total_length is not None
        and total_length > 5
    ):

        remaining = (
            total_length
            - current_time
        )

        if 0 <= remaining <= 2:

            pause_vlc()
            return

    end_episode_after_id = window.after(
        1000,
        poll_end_of_episode
    )


def set_sleep_timer(
    mode,
    minutes=None
):

    global sleep_timer_mode
    global sleep_timer_minutes

    sleep_timer_mode = mode

    if minutes is not None:
        sleep_timer_minutes = minutes

    save_settings()

    if mode == "off":

        cancel_sleep_timer()

        timer_status_label.config(
            text="Sleep Timer: Off"
        )

        status_label.config(
            text="Sleep timer disabled."
        )

    elif mode == "end_episode":

        timer_status_label.config(
            text="Sleep Timer: End of current episode"
        )

        status_label.config(
            text=(
                "Sleep timer will pause VLC "
                "at the end of the current episode."
            )
        )

        if (
            current_vlc_process
            and current_vlc_process.poll() is None
        ):
            start_sleep_timer()

    else:

        timer_status_label.config(
            text=f"Sleep Timer: {minutes} min"
        )

        status_label.config(
            text=f"Sleep timer set for {minutes} minutes."
        )

        if (
            current_vlc_process
            and current_vlc_process.poll() is None
        ):
            start_sleep_timer()


def custom_sleep_timer():

    minutes = simpledialog.askinteger(
        "Custom Sleep Timer",
        "Pause VLC after how many minutes?",
        parent=window,
        minvalue=1,
        maxvalue=1440
    )

    if minutes is None:
        return

    set_sleep_timer(
        "minutes",
        minutes
    )


def sleep_timer_dialog():

    dialog = tk.Toplevel(
        window
    )

    dialog.title(
        "Witching Hour - Sleep Timer"
    )

    dialog.geometry(
        "430x430"
    )

    dialog.resizable(
        False,
        False
    )

    dialog.configure(
        bg=BLACK
    )

    dialog.transient(
        window
    )

    tk.Label(
        dialog,
        text="🌙  SLEEP TIMER",
        font=(
            "Arial",
            19,
            "bold"
        ),
        bg=BLACK,
        fg=ORANGE
    ).pack(
        pady=(
            20,
            5
        )
    )

    tk.Label(
        dialog,
        text=(
            "When the timer expires, Witching Hour\n"
            "will pause the VLC session it launched."
        ),
        font=(
            "Arial",
            10
        ),
        justify="center",
        bg=BLACK,
        fg=LIGHT_GRAY
    ).pack(
        pady=(
            0,
            15
        )
    )

    options = [
        (
            "Off",
            "off",
            None
        ),
        (
            "30 Minutes",
            "minutes",
            30
        ),
        (
            "1 Hour",
            "minutes",
            60
        ),
        (
            "2 Hours",
            "minutes",
            120
        ),
        (
            "3 Hours",
            "minutes",
            180
        ),
        (
            "End of Current Episode",
            "end_episode",
            None
        )
    ]

    for text, mode, minutes in options:

        def choose(
            selected_mode=mode,
            selected_minutes=minutes
        ):

            set_sleep_timer(
                selected_mode,
                selected_minutes
            )

            dialog.destroy()

        tk.Button(
            dialog,
            text=text,
            command=choose,
            width=28,
            bg=PANEL_BLACK,
            fg=ORANGE,
            activebackground=ORANGE,
            activeforeground=BLACK,
            font=(
                "Arial",
                10,
                "bold"
            ),
            relief=tk.FLAT,
            pady=6,
            cursor="hand2"
        ).pack(
            pady=3
        )

    tk.Button(
        dialog,
        text="Custom...",
        command=lambda: (
            dialog.destroy(),
            custom_sleep_timer()
        ),
        width=28,
        bg=DARK_PURPLE,
        fg=WHITE,
        activebackground=PURPLE,
        activeforeground=WHITE,
        font=(
            "Arial",
            10,
            "bold"
        ),
        relief=tk.FLAT,
        pady=6,
        cursor="hand2"
    ).pack(
        pady=(
            8,
            3
        )
    )


# ============================================================
# SEARCH
# ============================================================

def filter_show_list(
    event=None
):

    global filtered_shows

    search_text = search_var.get().strip().lower()

    if search_text:

        filtered_shows = [
            show
            for show in shows
            if search_text in show.lower()
        ]

    else:

        filtered_shows = shows.copy()

    show_list.delete(
        0,
        tk.END
    )

    for show in filtered_shows:

        show_list.insert(
            tk.END,
            f"  {show}"
        )

    show_list.xview_moveto(
        0
    )

    if search_text:

        search_count_label.config(
            text=(
                f"{len(filtered_shows)} match"
                if len(filtered_shows) == 1
                else f"{len(filtered_shows)} matches"
            )
        )

    else:

        search_count_label.config(
            text=f"{len(filtered_shows)} shows"
        )


def clear_search():

    search_var.set(
        ""
    )

    filter_show_list()

    search_entry.focus_set()


def escape_clear_search(
    event=None
):

    if search_var.get():
        clear_search()


# ============================================================
# WATCH ORDER
# ============================================================

def refresh_watch_order(
    selected_index=None
):

    order_list.delete(
        0,
        tk.END
    )

    for show in watch_order:

        order_list.insert(
            tk.END,
            show
        )

    order_list.xview_moveto(
        0
    )

    if selected_index is not None:

        if (
            0 <= selected_index
            < len(watch_order)
        ):

            order_list.selection_set(
                selected_index
            )

            order_list.activate(
                selected_index
            )

            order_list.see(
                selected_index
            )

    watch_count_label.config(
        text=(
            f"{len(watch_order)} show"
            if len(watch_order) == 1
            else f"{len(watch_order)} shows"
        )
    )

    update_individual_controls()

    save_settings()


def add_to_watch_order():

    selected_indices = show_list.curselection()

    if not selected_indices:

        status_label.config(
            text="Select a show first."
        )

        return

    added = 0

    for index in selected_indices:

        if index >= len(filtered_shows):
            continue

        show = filtered_shows[
            index
        ]

        if show not in watch_order:

            watch_order.append(
                show
            )

            added += 1

    refresh_watch_order()

    if added:

        status_label.config(
            text=(
                f"Added {added} show(s) "
                "to the watch order."
            )
        )

    else:

        status_label.config(
            text=(
                "Selected show is already "
                "in the watch order."
            )
        )


def double_click_add(
    event=None
):

    add_to_watch_order()


def remove_from_watch_order():

    selected = order_list.curselection()

    if not selected:

        status_label.config(
            text=(
                "Select a show from "
                "the watch order first."
            )
        )

        return

    index = selected[0]

    removed_show = watch_order[
        index
    ]

    del watch_order[
        index
    ]

    individual_counts.pop(
        removed_show,
        None
    )

    refresh_watch_order()

    status_label.config(
        text=f"Removed {removed_show}."
    )


def move_up():

    selected = order_list.curselection()

    if not selected:
        return

    index = selected[0]

    if index <= 0:
        return

    watch_order[
        index - 1
    ], watch_order[
        index
    ] = (
        watch_order[index],
        watch_order[index - 1]
    )

    refresh_watch_order(
        index - 1
    )


def move_down():

    selected = order_list.curselection()

    if not selected:
        return

    index = selected[0]

    if index >= len(
        watch_order
    ) - 1:
        return

    watch_order[
        index
    ], watch_order[
        index + 1
    ] = (
        watch_order[index + 1],
        watch_order[index]
    )

    refresh_watch_order(
        index + 1
    )


def shuffle_watch_order():

    if len(watch_order) < 2:

        status_label.config(
            text=(
                "Add at least two shows "
                "before shuffling."
            )
        )

        return

    random.shuffle(
        watch_order
    )

    refresh_watch_order()

    status_label.config(
        text="Watch order shuffled. 🎲"
    )


def clear_watch_order():

    if not watch_order:
        return

    confirmed = messagebox.askyesno(
        "Clear Watch Order?",
        (
            "Remove every show from "
            "the current watch order?"
        )
    )

    if not confirmed:
        return

    watch_order.clear()

    refresh_watch_order()

    status_label.config(
        text="Watch order cleared."
    )


# ============================================================
# DRAG AND DROP WATCH ORDER
# ============================================================

drag_start_index = None


def drag_start(
    event
):

    global drag_start_index

    drag_start_index = order_list.nearest(
        event.y
    )


def drag_end(
    event
):

    global drag_start_index

    if drag_start_index is None:
        return

    if not watch_order:
        return

    destination = order_list.nearest(
        event.y
    )

    if (
        destination < 0
        or destination >= len(watch_order)
    ):

        drag_start_index = None
        return

    if destination == drag_start_index:

        drag_start_index = None
        return

    show = watch_order.pop(
        drag_start_index
    )

    watch_order.insert(
        destination,
        show
    )

    refresh_watch_order(
        destination
    )

    drag_start_index = None


# ============================================================
# EPISODE COUNT OPTIONS
# ============================================================

def change_episode_mode():

    global episode_mode

    episode_mode = mode_var.get()

    update_individual_controls()

    save_settings()

    if episode_mode == "universal":

        status_label.config(
            text="Universal episode count selected."
        )

    else:

        status_label.config(
            text=(
                "Select a Watch Order show "
                "to set its episode count."
            )
        )


def update_individual_controls():

    if episode_mode != "individual":

        individual_label.config(
            text="Individual mode is off."
        )

        individual_entry.delete(
            0,
            tk.END
        )

        return

    selected = order_list.curselection()

    if not selected:

        individual_label.config(
            text="Select a show from Watch Order."
        )

        individual_entry.delete(
            0,
            tk.END
        )

        return

    index = selected[0]

    if index >= len(watch_order):
        return

    show = watch_order[
        index
    ]

    count = individual_counts.get(
        show,
        3
    )

    individual_label.config(
        text=f"Episodes for {show}:"
    )

    individual_entry.delete(
        0,
        tk.END
    )

    individual_entry.insert(
        0,
        str(count)
    )


def save_individual_count():

    if episode_mode != "individual":

        status_label.config(
            text="Switch to Individual mode first."
        )

        return

    selected = order_list.curselection()

    if not selected:

        status_label.config(
            text="Select a Watch Order show first."
        )

        return

    try:

        count = int(
            individual_entry.get()
        )

        if count < 1:
            raise ValueError

    except ValueError:

        status_label.config(
            text="Enter a valid episode count."
        )

        return

    show = watch_order[
        selected[0]
    ]

    individual_counts[
        show
    ] = count

    save_settings()

    status_label.config(
        text=(
            f"{show} set to "
            f"{count} episode(s)."
        )
    )


def watch_order_selected(
    event=None
):

    update_individual_controls()


def change_start_mode():

    global start_mode

    start_mode = start_mode_var.get()

    save_settings()

    if start_mode == "memory":

        status_label.config(
            text=(
                "Playback will continue "
                "from memory."
            )
        )

    else:

        status_label.config(
            text=(
                "A random starting episode "
                "will be selected."
            )
        )


# ============================================================
# LIBRARY MANAGEMENT
# ============================================================

def refresh_available_shows():

    scan_library()

    for show in watch_order[:]:

        if show not in show_paths:

            watch_order.remove(
                show
            )

            individual_counts.pop(
                show,
                None
            )

    filter_show_list()

    refresh_watch_order()

    if not library_folders:

        status_label.config(
            text="No library folders selected."
        )

    elif not shows:

        status_label.config(
            text=(
                "No shows found in "
                "the selected libraries."
            )
        )

    else:

        status_label.config(
            text=f"Found {len(shows)} show(s)."
        )


def add_library_folder():

    folder = filedialog.askdirectory(
        title="Choose a TV Library Folder"
    )

    if not folder:
        return

    folder = os.path.normpath(
        folder
    )

    normalized = [
        os.path.normcase(
            os.path.normpath(
                existing
            )
        )
        for existing in library_folders
    ]

    if os.path.normcase(
        folder
    ) in normalized:

        messagebox.showinfo(
            "Witching Hour",
            (
                "That folder is already "
                "in your library."
            )
        )

        return

    library_folders.append(
        folder
    )

    save_settings()

    refresh_available_shows()


def manage_library_folders():

    manager = tk.Toplevel(
        window
    )

    manager.title(
        "Witching Hour - Library Folders"
    )

    manager.geometry(
        "760x440"
    )

    manager.configure(
        bg=BLACK
    )

    manager.transient(
        window
    )

    tk.Label(
        manager,
        text="🎃 LIBRARY FOLDERS",
        font=(
            "Arial",
            18,
            "bold"
        ),
        bg=BLACK,
        fg=ORANGE
    ).pack(
        pady=(
            20,
            5
        )
    )

    tk.Label(
        manager,
        text=(
            "Witching Hour scans "
            "these folders for shows."
        ),
        font=(
            "Arial",
            10
        ),
        bg=BLACK,
        fg=WHITE
    ).pack(
        pady=(
            0,
            15
        )
    )

    folder_list = tk.Listbox(
        manager,
        font=(
            "Arial",
            11
        ),
        bg=DARK_BLACK,
        fg=WHITE,
        selectbackground=ORANGE,
        selectforeground=BLACK,
        activestyle="none",
        relief=tk.FLAT
    )

    folder_list.pack(
        fill=tk.BOTH,
        expand=True,
        padx=20,
        pady=10
    )

    def refresh_folder_list():

        folder_list.delete(
            0,
            tk.END
        )

        for folder in library_folders:

            folder_list.insert(
                tk.END,
                folder
            )

    def manager_add():

        folder = filedialog.askdirectory(
            title="Add TV Library Folder",
            parent=manager
        )

        if not folder:
            return

        folder = os.path.normpath(
            folder
        )

        normalized = [
            os.path.normcase(
                os.path.normpath(
                    existing
                )
            )
            for existing in library_folders
        ]

        if os.path.normcase(
            folder
        ) in normalized:

            messagebox.showinfo(
                "Witching Hour",
                (
                    "That folder is already "
                    "in your library."
                ),
                parent=manager
            )

            return

        library_folders.append(
            folder
        )

        save_settings()
        refresh_folder_list()
        refresh_available_shows()

    def manager_remove():

        selected = folder_list.curselection()

        if not selected:
            return

        index = selected[0]

        folder = library_folders[
            index
        ]

        confirmed = messagebox.askyesno(
            "Remove Library?",
            (
                "Stop scanning this folder?\n\n"
                f"{folder}\n\n"
                "No files will be deleted."
            ),
            parent=manager
        )

        if not confirmed:
            return

        del library_folders[
            index
        ]

        save_settings()
        refresh_folder_list()
        refresh_available_shows()

    button_frame = tk.Frame(
        manager,
        bg=BLACK
    )

    button_frame.pack(
        pady=20
    )

    tk.Button(
        button_frame,
        text="ADD FOLDER",
        command=manager_add,
        bg=ORANGE,
        fg=BLACK,
        font=(
            "Arial",
            10,
            "bold"
        ),
        relief=tk.FLAT,
        padx=15,
        pady=7
    ).pack(
        side=tk.LEFT,
        padx=5
    )

    tk.Button(
        button_frame,
        text="REMOVE SELECTED",
        command=manager_remove,
        bg=DARK_PURPLE,
        fg=WHITE,
        font=(
            "Arial",
            10,
            "bold"
        ),
        relief=tk.FLAT,
        padx=15,
        pady=7
    ).pack(
        side=tk.LEFT,
        padx=5
    )

    tk.Button(
        button_frame,
        text="DONE",
        command=manager.destroy,
        bg=PANEL_BLACK,
        fg=ORANGE,
        font=(
            "Arial",
            10,
            "bold"
        ),
        relief=tk.FLAT,
        padx=15,
        pady=7
    ).pack(
        side=tk.LEFT,
        padx=5
    )

    refresh_folder_list()


def first_launch_library_setup():

    if library_folders:
        return

    messagebox.showinfo(
        "Welcome to Witching Hour",
        (
            "Welcome to Witching Hour! 🎃\n\n"
            "Choose the folder containing "
            "your TV shows.\n\n"
            "You can add more library "
            "folders afterward."
        )
    )

    while True:

        folder = filedialog.askdirectory(
            title="Choose Your TV Library"
        )

        if not folder:
            break

        folder = os.path.normpath(
            folder
        )

        if folder not in library_folders:

            library_folders.append(
                folder
            )

        another = messagebox.askyesno(
            "Add Another Folder?",
            (
                "Would you like to add "
                "another TV library folder?"
            )
        )

        if not another:
            break

    save_settings()


# ============================================================
# OPEN FOLDER
# ============================================================

def open_selected_show_folder():

    selected = show_list.curselection()

    if not selected:
        return

    index = selected[0]

    if index >= len(filtered_shows):
        return

    show = filtered_shows[
        index
    ]

    folder = show_paths.get(
        show
    )

    if (
        folder
        and os.path.isdir(folder)
    ):

        os.startfile(
            folder
        )


def open_watch_show_folder():

    selected = order_list.curselection()

    if not selected:
        return

    show = watch_order[
        selected[0]
    ]

    folder = show_paths.get(
        show
    )

    if (
        folder
        and os.path.isdir(folder)
    ):

        os.startfile(
            folder
        )


# ============================================================
# RIGHT CLICK MENUS
# ============================================================

def show_available_context_menu(
    event
):

    index = show_list.nearest(
        event.y
    )

    if index < 0:
        return

    show_list.selection_clear(
        0,
        tk.END
    )

    show_list.selection_set(
        index
    )

    available_context_menu.tk_popup(
        event.x_root,
        event.y_root
    )


def show_order_context_menu(
    event
):

    index = order_list.nearest(
        event.y
    )

    if index < 0:
        return

    order_list.selection_clear(
        0,
        tk.END
    )

    order_list.selection_set(
        index
    )

    update_individual_controls()

    order_context_menu.tk_popup(
        event.x_root,
        event.y_root
    )


# ============================================================
# SAVED LINEUPS
# ============================================================

def save_current_lineup():

    if not watch_order:

        messagebox.showinfo(
            "Witching Hour",
            "There is no watch order to save."
        )

        return

    name = simpledialog.askstring(
        "Save Lineup",
        "Name this lineup:",
        parent=window
    )

    if not name:
        return

    saved_lineups[name] = {
        "watch_order": watch_order.copy(),
        "episode_mode": episode_mode,
        "universal_count": episode_entry.get(),
        "individual_counts": individual_counts.copy(),
        "start_mode": start_mode
    }

    save_lineups()
    rebuild_lineups_menu()

    status_label.config(
        text=f'Saved lineup "{name}".'
    )


def load_lineup(
    name
):

    global episode_mode
    global individual_counts
    global start_mode

    lineup = saved_lineups.get(
        name
    )

    if not lineup:
        return

    new_order = [
        show
        for show in lineup.get(
            "watch_order",
            []
        )
        if show in show_paths
    ]

    watch_order[:] = new_order

    episode_mode = lineup.get(
        "episode_mode",
        "universal"
    )

    individual_counts = lineup.get(
        "individual_counts",
        {}
    )

    start_mode = lineup.get(
        "start_mode",
        "memory"
    )

    mode_var.set(
        episode_mode
    )

    start_mode_var.set(
        start_mode
    )

    episode_entry.delete(
        0,
        tk.END
    )

    episode_entry.insert(
        0,
        str(
            lineup.get(
                "universal_count",
                3
            )
        )
    )

    refresh_watch_order()
    update_individual_controls()
    save_settings()

    status_label.config(
        text=f'Loaded lineup "{name}".'
    )


def delete_saved_lineup():

    if not saved_lineups:

        messagebox.showinfo(
            "Witching Hour",
            "There are no saved lineups."
        )

        return

    dialog = tk.Toplevel(
        window
    )

    dialog.title(
        "Delete Saved Lineup"
    )

    dialog.geometry(
        "400x350"
    )

    dialog.configure(
        bg=BLACK
    )

    tk.Label(
        dialog,
        text="DELETE SAVED LINEUP",
        font=(
            "Arial",
            14,
            "bold"
        ),
        bg=BLACK,
        fg=ORANGE
    ).pack(
        pady=15
    )

    lineup_list = tk.Listbox(
        dialog,
        bg=DARK_BLACK,
        fg=WHITE,
        selectbackground=PURPLE,
        selectforeground=WHITE,
        font=(
            "Arial",
            11
        )
    )

    lineup_list.pack(
        fill=tk.BOTH,
        expand=True,
        padx=20,
        pady=10
    )

    for name in sorted(
        saved_lineups.keys(),
        key=str.lower
    ):

        lineup_list.insert(
            tk.END,
            name
        )

    def delete_selected():

        selected = lineup_list.curselection()

        if not selected:
            return

        name = lineup_list.get(
            selected[0]
        )

        del saved_lineups[
            name
        ]

        save_lineups()
        rebuild_lineups_menu()

        dialog.destroy()

        status_label.config(
            text=f'Deleted lineup "{name}".'
        )

    tk.Button(
        dialog,
        text="DELETE",
        command=delete_selected,
        bg=DARK_PURPLE,
        fg=WHITE,
        font=(
            "Arial",
            10,
            "bold"
        ),
        relief=tk.FLAT,
        padx=20,
        pady=8
    ).pack(
        pady=15
    )


def rebuild_lineups_menu():

    lineups_menu.delete(
        0,
        tk.END
    )

    lineups_menu.add_command(
        label="Save Current Lineup...",
        command=save_current_lineup
    )

    lineups_menu.add_separator()

    if saved_lineups:

        for name in sorted(
            saved_lineups.keys(),
            key=str.lower
        ):

            lineups_menu.add_command(
                label=name,
                command=lambda lineup_name=name:
                load_lineup(
                    lineup_name
                )
            )

        lineups_menu.add_separator()

        lineups_menu.add_command(
            label="Delete Saved Lineup...",
            command=delete_saved_lineup
        )

    else:

        lineups_menu.add_command(
            label="No Saved Lineups",
            state=tk.DISABLED
        )


# ============================================================
# HISTORY
# ============================================================

def add_history_item(
    show,
    episode
):

    history_item = {
        "show": show,
        "season": episode[0],
        "episode": episode[1],
        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %I:%M %p"
        ),
        "source": "Local",
        "filepath": episode[2]
    }

    watch_history.append(
        history_item
    )

    save_history()


def add_history_from_session_item(
    item
):

    history_item = {
        "show": item.get(
            "show",
            ""
        ),
        "season": item.get(
            "season",
            1
        ),
        "episode": item.get(
            "episode",
            1
        ),
        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %I:%M %p"
        ),
        "source": "Local",
        "filepath": item.get(
            "path",
            ""
        )
    }

    watch_history.append(
        history_item
    )

    save_history()


def refresh_history():

    for item in history_tree.get_children():

        history_tree.delete(
            item
        )

    for history_item in reversed(
        watch_history
    ):

        history_tree.insert(
            "",
            tk.END,
            values=(
                history_item.get(
                    "show",
                    ""
                ),
                (
                    f"S{int(history_item.get('season', 1)):02d}"
                    f"E{int(history_item.get('episode', 1)):02d}"
                ),
                history_item.get(
                    "timestamp",
                    ""
                ),
                history_item.get(
                    "source",
                    "Local"
                )
            )
        )

    history_count_label.config(
        text=(
            f"{len(watch_history)} / "
            f"{history_limit} recently played"
        )
    )


def clear_history():

    if not watch_history:
        return

    confirmed = messagebox.askyesno(
        "Clear History?",
        (
            "Clear Witching Hour's "
            "recently played history?"
        )
    )

    if not confirmed:
        return

    watch_history.clear()

    save_history()
    refresh_history()

    status_label.config(
        text="History cleared."
    )


# ============================================================
# CLEAR RESUME DATA
# ============================================================

def clear_resume_data():

    confirmed = messagebox.askyesno(
        "Clear Resume Memory?",
        (
            "Clear the unfinished playlist and all saved "
            "in-episode timestamps?\n\n"
            "Episode numbers will remain in memory, but "
            "episodes will restart from the beginning."
        )
    )

    if not confirmed:
        return

    clear_unfinished_session()

    for show, memory in playback_memory.items():

        if isinstance(
            memory,
            dict
        ):
            memory["resume_time"] = 0

    save_memory()

    status_label.config(
        text="Unfinished playback resume memory cleared."
    )


# ============================================================
# SETTINGS WINDOW
# ============================================================

def open_settings():

    settings_window = tk.Toplevel(
        window
    )

    settings_window.title(
        "Witching Hour - Settings"
    )

    settings_window.geometry(
        "650x390"
    )

    settings_window.resizable(
        False,
        False
    )

    settings_window.configure(
        bg=BLACK
    )

    settings_window.transient(
        window
    )

    tk.Label(
        settings_window,
        text="⚙  SETTINGS",
        font=(
            "Arial",
            18,
            "bold"
        ),
        bg=BLACK,
        fg=ORANGE
    ).pack(
        pady=(
            20,
            15
        )
    )

    content = tk.Frame(
        settings_window,
        bg=PANEL_BLACK,
        highlightthickness=1,
        highlightbackground=DARK_ORANGE
    )

    content.pack(
        fill=tk.BOTH,
        expand=True,
        padx=25,
        pady=10
    )

    tk.Label(
        content,
        text="VLC executable:",
        bg=PANEL_BLACK,
        fg=WHITE,
        font=(
            "Arial",
            10,
            "bold"
        )
    ).pack(
        anchor="w",
        padx=15,
        pady=(
            15,
            5
        )
    )

    vlc_var = tk.StringVar(
        value=vlc_path
    )

    vlc_row = tk.Frame(
        content,
        bg=PANEL_BLACK
    )

    vlc_row.pack(
        fill=tk.X,
        padx=15
    )

    vlc_entry = tk.Entry(
        vlc_row,
        textvariable=vlc_var,
        bg=DARK_BLACK,
        fg=WHITE,
        insertbackground=WHITE
    )

    vlc_entry.pack(
        side=tk.LEFT,
        fill=tk.X,
        expand=True
    )

    def browse_vlc():

        path = filedialog.askopenfilename(
            title="Choose VLC Executable",
            parent=settings_window,
            filetypes=[
                (
                    "Executable",
                    "*.exe"
                ),
                (
                    "All Files",
                    "*.*"
                )
            ]
        )

        if path:
            vlc_var.set(
                path
            )

    tk.Button(
        vlc_row,
        text="BROWSE",
        command=browse_vlc,
        bg=DARK_PURPLE,
        fg=WHITE,
        relief=tk.FLAT
    ).pack(
        side=tk.LEFT,
        padx=(
            8,
            0
        )
    )

    tk.Label(
        content,
        text="History size:",
        bg=PANEL_BLACK,
        fg=WHITE,
        font=(
            "Arial",
            10,
            "bold"
        )
    ).pack(
        anchor="w",
        padx=15,
        pady=(
            20,
            5
        )
    )

    history_limit_var = tk.StringVar(
        value=str(
            history_limit
        )
    )

    tk.Entry(
        content,
        textvariable=history_limit_var,
        width=8,
        justify="center",
        bg=DARK_BLACK,
        fg=GOLD,
        insertbackground=WHITE
    ).pack(
        anchor="w",
        padx=15
    )

    tk.Label(
        content,
        text=(
            "Default is 100 recently "
            "launched episodes."
        ),
        bg=PANEL_BLACK,
        fg=GRAY,
        font=(
            "Arial",
            9
        )
    ).pack(
        anchor="w",
        padx=15,
        pady=(
            3,
            15
        )
    )

    def save_settings_window():

        global vlc_path
        global history_limit
        global watch_history

        new_path = vlc_var.get().strip()

        try:

            new_history_limit = int(
                history_limit_var.get()
            )

            if (
                new_history_limit < 1
                or new_history_limit > 1000
            ):
                raise ValueError

        except ValueError:

            messagebox.showerror(
                "Invalid History Size",
                (
                    "Enter a number "
                    "between 1 and 1000."
                ),
                parent=settings_window
            )

            return

        vlc_path = new_path
        history_limit = new_history_limit

        watch_history = watch_history[
            -history_limit:
        ]

        save_settings()
        save_history()
        refresh_history()

        settings_window.destroy()

        status_label.config(
            text="Settings saved."
        )

    tk.Button(
        settings_window,
        text="SAVE SETTINGS",
        command=save_settings_window,
        bg=ORANGE,
        fg=BLACK,
        font=(
            "Arial",
            11,
            "bold"
        ),
        relief=tk.FLAT,
        padx=25,
        pady=8
    ).pack(
        pady=15
    )


# ============================================================
# BUILD FRESH PLAYLIST
# ============================================================

def build_fresh_playlist():

    try:

        universal_count = int(
            episode_entry.get()
        )

        if universal_count < 1:
            raise ValueError

    except ValueError:

        status_label.config(
            text="Enter a valid episode count."
        )

        return None

    if episode_mode == "individual":

        selected = order_list.curselection()

        if selected:

            try:

                count = int(
                    individual_entry.get()
                )

                if count < 1:
                    raise ValueError

            except ValueError:

                status_label.config(
                    text=(
                        "Enter a valid individual "
                        "episode count."
                    )
                )

                return None

            individual_counts[
                watch_order[selected[0]]
            ] = count

    save_settings()

    session_items = []

    for show in watch_order:

        show_folder = show_paths.get(
            show
        )

        if not show_folder:
            continue

        episodes = find_episodes(
            show_folder
        )

        if not episodes:
            continue

        if episode_mode == "universal":

            number_of_episodes = universal_count

        else:

            number_of_episodes = individual_counts.get(
                show,
                3
            )

        if len(
            episodes
        ) < number_of_episodes:

            messagebox.showwarning(
                "Not Enough Episodes",
                (
                    f"{show} only has "
                    f"{len(episodes)} detected episode(s), "
                    f"but {number_of_episodes} were requested.\n\n"
                    "That show will be skipped."
                )
            )

            continue

        start_index = get_starting_index(
            show,
            episodes
        )

        for offset in range(
            number_of_episodes
        ):

            index = (
                start_index
                + offset
            ) % len(
                episodes
            )

            episode = episodes[
                index
            ]

            next_index = (
                index + 1
            ) % len(
                episodes
            )

            next_episode = episodes[
                next_index
            ]

            resume_time = get_resume_time_for_episode(
                show,
                episode
            )

            session_items.append(
                {
                    "show": show,
                    "season": episode[0],
                    "episode": episode[1],
                    "path": episode[2],
                    "resume_time": resume_time,
                    "next_season": next_episode[0],
                    "next_episode": next_episode[1]
                }
            )

    return session_items


# ============================================================
# LAUNCH VLC PLAYLIST
# ============================================================

def launch_session_items(
    items,
    resume_session=False
):

    global current_vlc_process
    global current_vlc_port
    global unfinished_session

    if not items:

        status_label.config(
            text="No episodes could be selected."
        )

        return

    current_vlc_port = find_free_port()

    command = [
        vlc_path,
        "--extraintf=rc",
        "--rc-quiet",
        f"--rc-host=127.0.0.1:{current_vlc_port}",
        "--no-one-instance"
    ]

    # --------------------------------------------------------
    # Each :start-time belongs to the media item immediately
    # before it, allowing different resume positions per item.
    # --------------------------------------------------------

    for item in items:

        filepath = item.get(
            "path"
        )

        if not filepath:
            continue

        command.append(
            filepath
        )

        try:

            item_resume_time = int(
                item.get(
                    "resume_time",
                    0
                )
            )

        except (
            TypeError,
            ValueError
        ):
            item_resume_time = 0

        if item_resume_time > 2:

            command.append(
                f":start-time={item_resume_time}"
            )

    creation_flags = 0

    if hasattr(
        subprocess,
        "CREATE_NO_WINDOW"
    ):

        creation_flags = (
            subprocess.CREATE_NO_WINDOW
        )

    try:

        current_vlc_process = subprocess.Popen(
            command,
            creationflags=creation_flags
        )

    except OSError as error:

        messagebox.showerror(
            "Playback Error",
            (
                "Witching Hour could not start VLC.\n\n"
                f"{error}"
            )
        )

        return

    # --------------------------------------------------------
    # CREATE NEW LIVE SESSION SNAPSHOT
    # --------------------------------------------------------

    unfinished_session = {
        "items": items,
        "current_index": 0,
        "current_time": int(
            items[0].get(
                "resume_time",
                0
            )
        ),
        "created": datetime.now().isoformat(
            timespec="seconds"
        ),
        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    save_unfinished_session()

    # History continues to mean "sent to VLC".
    for item in items:

        add_history_from_session_item(
            item
        )

    refresh_history()

    update_now_playing_from_session(
        0
    )

    if resume_session:

        status_label.config(
            text=(
                "Resuming unfinished playlist "
                "from your saved position. 🌙"
            )
        )

    else:

        status_label.config(
            text=(
                f"Playback started — "
                f"{len(items)} episode(s)."
            )
        )

    begin_playback_monitor()

    window.after(
        1500,
        start_sleep_timer
    )


# ============================================================
# RESUME SAVED SESSION
# ============================================================

def resume_saved_session():

    global unfinished_session

    if not has_valid_unfinished_session():

        clear_unfinished_session()

        messagebox.showinfo(
            "Witching Hour",
            (
                "The saved playback session "
                "could no longer be resumed."
            )
        )

        return False

    items = unfinished_session.get(
        "items",
        []
    )

    current_index = unfinished_session.get(
        "current_index",
        0
    )

    current_time = unfinished_session.get(
        "current_time",
        0
    )

    remaining_items = []

    for index in range(
        current_index,
        len(items)
    ):

        item = items[
            index
        ].copy()

        if not os.path.exists(
            item.get(
                "path",
                ""
            )
        ):
            continue

        if index == current_index:

            try:
                item[
                    "resume_time"
                ] = max(
                    0,
                    int(current_time)
                )

            except (
                TypeError,
                ValueError
            ):

                item[
                    "resume_time"
                ] = 0

        else:

            # Preserve any item-specific timestamp it may have.
            try:

                item[
                    "resume_time"
                ] = max(
                    0,
                    int(
                        item.get(
                            "resume_time",
                            0
                        )
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                item[
                    "resume_time"
                ] = 0

        remaining_items.append(
            item
        )

    if not remaining_items:

        clear_unfinished_session()

        return False

    launch_session_items(
        remaining_items,
        resume_session=True
    )

    return True


# ============================================================
# START PLAYBACK
# ============================================================

def start_playback():

    if not os.path.exists(
        vlc_path
    ):

        messagebox.showerror(
            "VLC Not Found",
            (
                "Witching Hour could not find VLC at:\n\n"
                f"{vlc_path}\n\n"
                "You can change this under "
                "File → Settings."
            )
        )

        return

    # --------------------------------------------------------
    # EXISTING VLC SESSION STILL RUNNING
    # --------------------------------------------------------

    if (
        current_vlc_process is not None
        and current_vlc_process.poll() is None
    ):

        messagebox.showinfo(
            "Playback Already Running",
            (
                "The VLC session launched by "
                "Witching Hour is still running."
            )
        )

        return

    # --------------------------------------------------------
    # OFFER TO RESUME UNFINISHED SESSION
    # --------------------------------------------------------

    if has_valid_unfinished_session():

        current_index = unfinished_session.get(
            "current_index",
            0
        )

        items = unfinished_session.get(
            "items",
            []
        )

        item = items[
            current_index
        ]

        seconds = unfinished_session.get(
            "current_time",
            0
        )

        try:
            seconds = int(
                seconds
            )

        except (
            TypeError,
            ValueError
        ):
            seconds = 0

        minutes = seconds // 60
        remaining_seconds = seconds % 60

        choice = messagebox.askyesnocancel(
            "Resume Unfinished Playback?",
            (
                "Witching Hour found an unfinished playlist.\n\n"
                f"Last show:\n"
                f"{item.get('show', 'Unknown')}\n\n"
                f"Episode: "
                f"S{int(item.get('season', 1)):02d}"
                f"E{int(item.get('episode', 1)):02d}\n"
                f"Position: "
                f"{minutes}:{remaining_seconds:02d}\n\n"
                "YES  = Resume the saved playlist\n"
                "NO   = Discard that playlist and start "
                "the current Watch Order\n"
                "CANCEL = Do nothing"
            )
        )

        if choice is None:

            return

        if choice is True:

            resume_saved_session()
            return

        # NO = discard old playlist but retain per-show
        # episode/timestamp memory.
        clear_unfinished_session()

    # --------------------------------------------------------
    # FRESH PLAYLIST
    # --------------------------------------------------------

    if not watch_order:

        status_label.config(
            text=(
                "Add at least one show "
                "to the watch order."
            )
        )

        return

    session_items = build_fresh_playlist()

    if not session_items:
        return

    launch_session_items(
        session_items,
        resume_session=False
    )


# ============================================================
# CLOSE PROGRAM
# ============================================================

def close_program():

    save_settings()

    # If VLC is still playing, the monitor has been saving
    # approximately every two seconds. Do not kill VLC and
    # do not erase its resume data.

    window.destroy()


# ============================================================
# GUI
# ============================================================

window = tk.Tk()

window.title(
    "🎃 Witching Hour"
)

window.geometry(
    "1180x940"
)

window.minsize(
    1050,
    820
)


# ============================================================
# COLORS
# ============================================================

BLACK = "#090909"
DARK_BLACK = "#111111"
PANEL_BLACK = "#151515"
LIGHT_BLACK = "#202020"

ORANGE = "#ff6a00"
BRIGHT_ORANGE = "#ff7b00"
DARK_ORANGE = "#b84800"

WHITE = "#f5f5f5"
LIGHT_GRAY = "#c8c8c8"
GRAY = "#888888"

PURPLE = "#7b2cbf"
DARK_PURPLE = "#3c096c"

GOLD = "#ffc857"


window.configure(
    bg=BLACK
)


# ============================================================
# MENU BAR
# ============================================================

menu_bar = tk.Menu(
    window
)

file_menu = tk.Menu(
    menu_bar,
    tearoff=0
)

file_menu.add_command(
    label="Add Library Folder...",
    command=add_library_folder
)

file_menu.add_command(
    label="Manage Library Folders...",
    command=manage_library_folders
)

file_menu.add_command(
    label="Rescan Library",
    command=refresh_available_shows
)

file_menu.add_separator()

file_menu.add_command(
    label="Sleep Timer...",
    command=sleep_timer_dialog
)

file_menu.add_separator()

file_menu.add_command(
    label="Clear Resume Memory...",
    command=clear_resume_data
)

file_menu.add_separator()

file_menu.add_command(
    label="Settings...",
    command=open_settings
)

file_menu.add_separator()

file_menu.add_command(
    label="Exit",
    command=close_program
)

menu_bar.add_cascade(
    label="File",
    menu=file_menu
)


lineups_menu = tk.Menu(
    menu_bar,
    tearoff=0
)

menu_bar.add_cascade(
    label="Lineups",
    menu=lineups_menu
)

window.config(
    menu=menu_bar
)


# ============================================================
# HEADER
# ============================================================

header_frame = tk.Frame(
    window,
    bg=BLACK
)

header_frame.pack(
    fill=tk.X,
    padx=25,
    pady=(
        16,
        4
    )
)

tk.Label(
    header_frame,
    text="🎃",
    font=(
        "Segoe UI Emoji",
        28
    ),
    bg=BLACK,
    fg=ORANGE
).pack(
    side=tk.LEFT,
    padx=10
)

tk.Label(
    header_frame,
    text="WITCHING HOUR",
    font=(
        "Arial",
        26,
        "bold"
    ),
    bg=BLACK,
    fg=ORANGE
).pack(
    side=tk.LEFT,
    expand=True
)

tk.Label(
    header_frame,
    text="🎃",
    font=(
        "Segoe UI Emoji",
        28
    ),
    bg=BLACK,
    fg=ORANGE
).pack(
    side=tk.RIGHT,
    padx=10
)

tk.Label(
    window,
    text=(
        "Your nightly descent into "
        "questionable television choices"
    ),
    font=(
        "Arial",
        10,
        "italic"
    ),
    bg=BLACK,
    fg=PURPLE
).pack(
    pady=(
        0,
        8
    )
)

tk.Frame(
    window,
    bg=ORANGE,
    height=2
).pack(
    fill=tk.X,
    padx=55,
    pady=(
        0,
        10
    )
)


# ============================================================
# NOTEBOOK
# ============================================================

style = ttk.Style()

style.theme_use(
    "default"
)

style.configure(
    "TNotebook",
    background=BLACK,
    borderwidth=0
)

style.configure(
    "TNotebook.Tab",
    background=PANEL_BLACK,
    foreground=WHITE,
    padding=[
        18,
        8
    ],
    font=(
        "Arial",
        10,
        "bold"
    )
)

style.map(
    "TNotebook.Tab",
    background=[
        (
            "selected",
            ORANGE
        )
    ],
    foreground=[
        (
            "selected",
            BLACK
        )
    ]
)

notebook = ttk.Notebook(
    window
)

notebook.pack(
    fill=tk.BOTH,
    expand=True,
    padx=20,
    pady=5
)


main_tab = tk.Frame(
    notebook,
    bg=BLACK
)

history_tab = tk.Frame(
    notebook,
    bg=BLACK
)

notebook.add(
    main_tab,
    text="🎃  Watch"
)

notebook.add(
    history_tab,
    text="📜  History"
)


# ============================================================
# SEARCH BAR
# ============================================================

search_outer = tk.Frame(
    main_tab,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE
)

search_outer.pack(
    fill=tk.X,
    padx=5,
    pady=(
        5,
        10
    )
)

tk.Label(
    search_outer,
    text="🔎",
    font=(
        "Segoe UI Emoji",
        14
    ),
    bg=PANEL_BLACK,
    fg=ORANGE
).pack(
    side=tk.LEFT,
    padx=(
        12,
        5
    ),
    pady=8
)

search_var = tk.StringVar()

search_entry = tk.Entry(
    search_outer,
    textvariable=search_var,
    font=(
        "Arial",
        12
    ),
    bg=DARK_BLACK,
    fg=WHITE,
    insertbackground=WHITE,
    relief=tk.FLAT
)

search_entry.pack(
    side=tk.LEFT,
    fill=tk.X,
    expand=True,
    padx=5,
    pady=8
)

search_entry.bind(
    "<KeyRelease>",
    filter_show_list
)

search_entry.bind(
    "<Escape>",
    escape_clear_search
)

search_count_label = tk.Label(
    search_outer,
    text="0 shows",
    font=(
        "Arial",
        9
    ),
    bg=PANEL_BLACK,
    fg=GRAY
)

search_count_label.pack(
    side=tk.LEFT,
    padx=10
)

tk.Button(
    search_outer,
    text="✕",
    command=clear_search,
    font=(
        "Arial",
        10,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=ORANGE,
    activebackground=ORANGE,
    activeforeground=BLACK,
    relief=tk.FLAT,
    cursor="hand2"
).pack(
    side=tk.RIGHT,
    padx=10
)


# ============================================================
# MAIN LIST AREA
# ============================================================

main_frame = tk.Frame(
    main_tab,
    bg=BLACK
)

main_frame.pack(
    fill=tk.BOTH,
    expand=True,
    padx=5
)


# ============================================================
# AVAILABLE SHOWS
# ============================================================

available_frame = tk.Frame(
    main_frame,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE
)

available_frame.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
    padx=(
        0,
        8
    )
)

tk.Label(
    available_frame,
    text="🎃  AVAILABLE SHOWS",
    font=(
        "Arial",
        14,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
).pack(
    anchor="w",
    padx=12,
    pady=(
        10,
        2
    )
)

tk.Label(
    available_frame,
    text=(
        "Double-click to add • "
        "Right-click for options"
    ),
    font=(
        "Arial",
        9
    ),
    bg=PANEL_BLACK,
    fg=LIGHT_GRAY
).pack(
    anchor="w",
    padx=15,
    pady=(
        0,
        7
    )
)

available_list_frame = tk.Frame(
    available_frame,
    bg=PANEL_BLACK
)

available_list_frame.pack(
    fill=tk.BOTH,
    expand=True,
    padx=12,
    pady=(
        0,
        12
    )
)

show_list = tk.Listbox(
    available_list_frame,
    selectmode=tk.EXTENDED,
    font=(
        "Arial",
        12
    ),
    bg=DARK_BLACK,
    fg=WHITE,
    selectbackground=ORANGE,
    selectforeground=BLACK,
    activestyle="none",
    relief=tk.FLAT
)

available_x_scrollbar = tk.Scrollbar(
    available_list_frame,
    orient=tk.HORIZONTAL,
    command=show_list.xview
)

show_list.configure(
    xscrollcommand=available_x_scrollbar.set
)

show_list.pack(
    side=tk.TOP,
    fill=tk.BOTH,
    expand=True
)

available_x_scrollbar.pack(
    side=tk.BOTTOM,
    fill=tk.X
)

show_list.bind(
    "<Double-Button-1>",
    double_click_add
)

show_list.bind(
    "<Button-3>",
    show_available_context_menu
)


# ============================================================
# CENTER BUTTONS
# ============================================================

middle_frame = tk.Frame(
    main_frame,
    bg=BLACK
)

middle_frame.pack(
    side=tk.LEFT,
    padx=8
)

tk.Label(
    middle_frame,
    text="☠",
    font=(
        "Segoe UI Symbol",
        20
    ),
    bg=BLACK,
    fg=PURPLE
).pack(
    pady=(
        20,
        10
    )
)


def action_button(
    text,
    command
):

    button = tk.Button(
        middle_frame,
        text=text,
        command=command,
        width=13,
        bg=DARK_BLACK,
        fg=ORANGE,
        activebackground=ORANGE,
        activeforeground=BLACK,
        font=(
            "Arial",
            10,
            "bold"
        ),
        relief=tk.FLAT,
        pady=6,
        cursor="hand2"
    )

    button.pack(
        pady=4
    )

    return button


action_button(
    "ADD  →",
    add_to_watch_order
)

action_button(
    "←  REMOVE",
    remove_from_watch_order
)

action_button(
    "▲  MOVE UP",
    move_up
)

action_button(
    "▼  MOVE DOWN",
    move_down
)

action_button(
    "🎲  SHUFFLE",
    shuffle_watch_order
)

tk.Button(
    middle_frame,
    text="☠  CLEAR",
    command=clear_watch_order,
    width=13,
    bg=DARK_PURPLE,
    fg=WHITE,
    activebackground=PURPLE,
    activeforeground=WHITE,
    font=(
        "Arial",
        10,
        "bold"
    ),
    relief=tk.FLAT,
    pady=6,
    cursor="hand2"
).pack(
    pady=(
        15,
        4
    )
)


# ============================================================
# WATCH ORDER
# ============================================================

order_frame = tk.Frame(
    main_frame,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE
)

order_frame.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
    padx=(
        8,
        0
    )
)

order_title_frame = tk.Frame(
    order_frame,
    bg=PANEL_BLACK
)

order_title_frame.pack(
    fill=tk.X,
    padx=12,
    pady=(
        10,
        2
    )
)

tk.Label(
    order_title_frame,
    text="👻  WATCH ORDER",
    font=(
        "Arial",
        14,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
).pack(
    side=tk.LEFT
)

watch_count_label = tk.Label(
    order_title_frame,
    text="0 shows",
    font=(
        "Arial",
        9
    ),
    bg=PANEL_BLACK,
    fg=GRAY
)

watch_count_label.pack(
    side=tk.RIGHT
)

tk.Label(
    order_frame,
    text=(
        "Drag shows to reorder • "
        "Right-click for options"
    ),
    font=(
        "Arial",
        9
    ),
    bg=PANEL_BLACK,
    fg=LIGHT_GRAY
).pack(
    anchor="w",
    padx=15,
    pady=(
        0,
        7
    )
)

order_list_frame = tk.Frame(
    order_frame,
    bg=PANEL_BLACK
)

order_list_frame.pack(
    fill=tk.BOTH,
    expand=True,
    padx=12,
    pady=(
        0,
        12
    )
)

order_list = tk.Listbox(
    order_list_frame,
    selectmode=tk.SINGLE,
    font=(
        "Arial",
        12
    ),
    bg=DARK_BLACK,
    fg=WHITE,
    selectbackground=PURPLE,
    selectforeground=WHITE,
    activestyle="none",
    relief=tk.FLAT
)

order_x_scrollbar = tk.Scrollbar(
    order_list_frame,
    orient=tk.HORIZONTAL,
    command=order_list.xview
)

order_list.configure(
    xscrollcommand=order_x_scrollbar.set
)

order_list.pack(
    side=tk.TOP,
    fill=tk.BOTH,
    expand=True
)

order_x_scrollbar.pack(
    side=tk.BOTTOM,
    fill=tk.X
)

order_list.bind(
    "<<ListboxSelect>>",
    watch_order_selected
)

order_list.bind(
    "<ButtonPress-1>",
    drag_start
)

order_list.bind(
    "<ButtonRelease-1>",
    drag_end
)

order_list.bind(
    "<Button-3>",
    show_order_context_menu
)


# ============================================================
# RIGHT CLICK MENUS
# ============================================================

available_context_menu = tk.Menu(
    window,
    tearoff=0
)

available_context_menu.add_command(
    label="Add to Watch Order",
    command=add_to_watch_order
)

available_context_menu.add_command(
    label="Open Folder",
    command=open_selected_show_folder
)


order_context_menu = tk.Menu(
    window,
    tearoff=0
)

order_context_menu.add_command(
    label="Remove from Watch Order",
    command=remove_from_watch_order
)

order_context_menu.add_command(
    label="Move Up",
    command=move_up
)

order_context_menu.add_command(
    label="Move Down",
    command=move_down
)

order_context_menu.add_separator()

order_context_menu.add_command(
    label="Open Folder",
    command=open_watch_show_folder
)


# ============================================================
# OPTIONS AREA
# ============================================================

options_frame = tk.Frame(
    main_tab,
    bg=BLACK
)

options_frame.pack(
    fill=tk.X,
    padx=5,
    pady=10
)


# ============================================================
# EPISODE COUNT
# ============================================================

episode_panel = tk.Frame(
    options_frame,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE
)

episode_panel.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
    padx=(
        0,
        8
    )
)

tk.Label(
    episode_panel,
    text="🎃  EPISODE COUNT",
    font=(
        "Arial",
        13,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
).pack(
    pady=(
        8,
        4
    )
)

mode_var = tk.StringVar(
    value=episode_mode
)

mode_row = tk.Frame(
    episode_panel,
    bg=PANEL_BLACK
)

mode_row.pack(
    pady=3
)

tk.Radiobutton(
    mode_row,
    text="Universal",
    variable=mode_var,
    value="universal",
    command=change_episode_mode,
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=ORANGE,
    selectcolor=DARK_BLACK
).pack(
    side=tk.LEFT,
    padx=10
)

tk.Radiobutton(
    mode_row,
    text="Individual",
    variable=mode_var,
    value="individual",
    command=change_episode_mode,
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=PURPLE,
    selectcolor=DARK_BLACK
).pack(
    side=tk.LEFT,
    padx=10
)

universal_row = tk.Frame(
    episode_panel,
    bg=PANEL_BLACK
)

universal_row.pack(
    pady=3
)

tk.Label(
    universal_row,
    text="Episodes per show:",
    bg=PANEL_BLACK,
    fg=LIGHT_GRAY
).pack(
    side=tk.LEFT
)

episode_entry = tk.Entry(
    universal_row,
    width=5,
    justify="center",
    bg=DARK_BLACK,
    fg=GOLD,
    insertbackground=WHITE,
    font=(
        "Arial",
        11,
        "bold"
    )
)

episode_entry.insert(
    0,
    str(
        settings.get(
            "universal_count",
            3
        )
    )
)

episode_entry.pack(
    side=tk.LEFT,
    padx=6
)

individual_row = tk.Frame(
    episode_panel,
    bg=PANEL_BLACK
)

individual_row.pack(
    pady=(
        3,
        8
    )
)

individual_label = tk.Label(
    individual_row,
    text="Individual mode is off.",
    bg=PANEL_BLACK,
    fg=GRAY,
    font=(
        "Arial",
        9
    )
)

individual_label.pack(
    side=tk.LEFT,
    padx=5
)

individual_entry = tk.Entry(
    individual_row,
    width=5,
    justify="center",
    bg=DARK_BLACK,
    fg=GOLD,
    insertbackground=WHITE
)

individual_entry.pack(
    side=tk.LEFT,
    padx=5
)

tk.Button(
    individual_row,
    text="SAVE",
    command=save_individual_count,
    bg=DARK_BLACK,
    fg=ORANGE,
    activebackground=ORANGE,
    activeforeground=BLACK,
    relief=tk.FLAT
).pack(
    side=tk.LEFT,
    padx=5
)


# ============================================================
# START MODE
# ============================================================

start_panel = tk.Frame(
    options_frame,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE
)

start_panel.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
    padx=(
        8,
        0
    )
)

tk.Label(
    start_panel,
    text="🎲  STARTING EPISODE",
    font=(
        "Arial",
        13,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
).pack(
    pady=(
        8,
        5
    )
)

start_mode_var = tk.StringVar(
    value=start_mode
)

tk.Radiobutton(
    start_panel,
    text="🧠 Continue from Memory",
    variable=start_mode_var,
    value="memory",
    command=change_start_mode,
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=ORANGE,
    selectcolor=DARK_BLACK
).pack(
    anchor="w",
    padx=25,
    pady=3
)

tk.Radiobutton(
    start_panel,
    text="🎲 Random Starting Episode",
    variable=start_mode_var,
    value="random",
    command=change_start_mode,
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=PURPLE,
    selectcolor=DARK_BLACK
).pack(
    anchor="w",
    padx=25,
    pady=(
        3,
        9
    )
)


# ============================================================
# NOW PLAYING / TIMER
# ============================================================

playback_info_frame = tk.Frame(
    main_tab,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_PURPLE
)

playback_info_frame.pack(
    fill=tk.X,
    padx=5,
    pady=(
        0,
        8
    )
)

now_playing_label = tk.Label(
    playback_info_frame,
    text="Now Playing: Nothing yet",
    bg=PANEL_BLACK,
    fg=WHITE,
    font=(
        "Arial",
        9,
        "bold"
    )
)

now_playing_label.pack(
    side=tk.LEFT,
    padx=12,
    pady=7
)

next_up_label = tk.Label(
    playback_info_frame,
    text="Next Up: —",
    bg=PANEL_BLACK,
    fg=LIGHT_GRAY,
    font=(
        "Arial",
        9
    )
)

next_up_label.pack(
    side=tk.LEFT,
    padx=20
)

timer_status_label = tk.Label(
    playback_info_frame,
    text="Sleep Timer: Off",
    bg=PANEL_BLACK,
    fg=GOLD,
    font=(
        "Arial",
        9
    )
)

timer_status_label.pack(
    side=tk.RIGHT,
    padx=12
)


# ============================================================
# START PLAYBACK
# ============================================================

tk.Button(
    main_tab,
    text="▶   START PLAYBACK   🎃",
    command=start_playback,
    bg=ORANGE,
    fg=BLACK,
    activebackground=GOLD,
    activeforeground=BLACK,
    font=(
        "Arial",
        16,
        "bold"
    ),
    relief=tk.FLAT,
    padx=35,
    pady=10,
    cursor="hand2"
).pack(
    pady=(
        3,
        8
    )
)


# ============================================================
# HISTORY TAB
# ============================================================

history_header = tk.Frame(
    history_tab,
    bg=BLACK
)

history_header.pack(
    fill=tk.X,
    padx=15,
    pady=15
)

tk.Label(
    history_header,
    text="📜  RECENTLY PLAYED",
    font=(
        "Arial",
        18,
        "bold"
    ),
    bg=BLACK,
    fg=ORANGE
).pack(
    side=tk.LEFT
)

history_count_label = tk.Label(
    history_header,
    text="0 / 100 recently played",
    font=(
        "Arial",
        9
    ),
    bg=BLACK,
    fg=GRAY
)

history_count_label.pack(
    side=tk.RIGHT,
    padx=10
)

history_columns = (
    "show",
    "episode",
    "date",
    "source"
)

history_tree = ttk.Treeview(
    history_tab,
    columns=history_columns,
    show="headings"
)

history_tree.heading(
    "show",
    text="Show"
)

history_tree.heading(
    "episode",
    text="Episode"
)

history_tree.heading(
    "date",
    text="Date / Time"
)

history_tree.heading(
    "source",
    text="Source"
)

history_tree.column(
    "show",
    width=420,
    anchor="w"
)

history_tree.column(
    "episode",
    width=100,
    anchor="center"
)

history_tree.column(
    "date",
    width=200,
    anchor="center"
)

history_tree.column(
    "source",
    width=120,
    anchor="center"
)

history_tree.pack(
    fill=tk.BOTH,
    expand=True,
    padx=15,
    pady=(
        0,
        10
    )
)

tk.Label(
    history_tab,
    text=(
        "History records episodes Witching Hour "
        "sent to VLC. Playback resume memory is "
        "tracked separately."
    ),
    bg=BLACK,
    fg=GRAY,
    font=(
        "Arial",
        9,
        "italic"
    )
).pack(
    pady=5
)

tk.Button(
    history_tab,
    text="CLEAR HISTORY",
    command=clear_history,
    bg=DARK_PURPLE,
    fg=WHITE,
    activebackground=PURPLE,
    activeforeground=WHITE,
    font=(
        "Arial",
        10,
        "bold"
    ),
    relief=tk.FLAT,
    padx=20,
    pady=7
).pack(
    pady=(
        5,
        15
    )
)


# ============================================================
# STATUS BAR
# ============================================================

status_frame = tk.Frame(
    window,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_PURPLE
)

status_frame.pack(
    fill=tk.X,
    padx=20,
    pady=(
        5,
        15
    )
)

tk.Label(
    status_frame,
    text="🎃",
    bg=PANEL_BLACK,
    fg=ORANGE,
    font=(
        "Segoe UI Emoji",
        13
    )
).pack(
    side=tk.LEFT,
    padx=(
        10,
        5
    ),
    pady=6
)

status_label = tk.Label(
    status_frame,
    text="Ready.",
    bg=PANEL_BLACK,
    fg=WHITE,
    font=(
        "Arial",
        9
    )
)

status_label.pack(
    side=tk.LEFT,
    pady=6
)


# ============================================================
# INITIALIZE
# ============================================================

rebuild_lineups_menu()

first_launch_library_setup()

refresh_available_shows()

refresh_history()

update_individual_controls()


# ------------------------------------------------------------
# DISPLAY TIMER STATE
# ------------------------------------------------------------

if sleep_timer_mode == "off":

    timer_status_label.config(
        text="Sleep Timer: Off"
    )

elif sleep_timer_mode == "end_episode":

    timer_status_label.config(
        text=(
            "Sleep Timer: "
            "End of current episode"
        )
    )

else:

    timer_status_label.config(
        text=(
            f"Sleep Timer: "
            f"{sleep_timer_minutes} min"
        )
    )


# ------------------------------------------------------------
# SHOW SAVED SESSION IN STATUS BAR
# ------------------------------------------------------------

if has_valid_unfinished_session():

    saved_index = unfinished_session.get(
        "current_index",
        0
    )

    saved_items = unfinished_session.get(
        "items",
        []
    )

    if (
        saved_items
        and 0 <= saved_index < len(saved_items)
    ):

        saved_item = saved_items[
            saved_index
        ]

        status_label.config(
            text=(
                "Unfinished playback detected: "
                f"{saved_item.get('show', 'Unknown')} "
                f"S{int(saved_item.get('season', 1)):02d}"
                f"E{int(saved_item.get('episode', 1)):02d}. "
                "Press START PLAYBACK to resume."
            )
        )


# ============================================================
# WINDOW CLOSE
# ============================================================

window.protocol(
    "WM_DELETE_WINDOW",
    close_program
)


# ============================================================
# START WITCHING HOUR
# ============================================================

window.mainloop()