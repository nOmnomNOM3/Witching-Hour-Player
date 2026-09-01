import os
import shutil
import sys

APP_NAME = "WitchingHour"

DATA_FILES = (
    "settings.json",
    "playback_memory.json",
    "watch_history.json",
    "unfinished_session.json",
    "library_folders.json",
)


def program_folder():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def user_data_folder():
    roaming = os.environ.get("APPDATA")
    if not roaming:
        roaming = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    folder = os.path.join(roaming, APP_NAME)
    os.makedirs(folder, exist_ok=True)
    return folder


def bundle_folder():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return program_folder()


def asset_path(*parts):
    return os.path.join(bundle_folder(), "assets", *parts)


def data_path(name):
    return os.path.join(user_data_folder(), name)


def migrate_legacy_files():
    source_dir = program_folder()
    dest_dir = user_data_folder()
    if os.path.normcase(os.path.abspath(source_dir)) == os.path.normcase(
        os.path.abspath(dest_dir)
    ):
        return
    for name in DATA_FILES:
        src = os.path.join(source_dir, name)
        dest = os.path.join(dest_dir, name)
        if os.path.isfile(src) and not os.path.isfile(dest):
            try:
                shutil.copy2(src, dest)
            except OSError:
                pass


migrate_legacy_files()

SETTINGS_FILE = data_path("settings.json")
MEMORY_FILE = data_path("playback_memory.json")
HISTORY_FILE = data_path("watch_history.json")
SESSION_FILE = data_path("unfinished_session.json")
LEGACY_LIBRARY_FILE = data_path("library_folders.json")