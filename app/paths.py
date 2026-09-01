import os
import sys


def program_folder():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_path(name):
    return os.path.join(program_folder(), name)


SETTINGS_FILE = data_path("settings.json")
MEMORY_FILE = data_path("playback_memory.json")
HISTORY_FILE = data_path("watch_history.json")
SESSION_FILE = data_path("unfinished_session.json")
LEGACY_LIBRARY_FILE = data_path("library_folders.json")
