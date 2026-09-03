from . import paths
from .store import load_json, save_json

DEFAULTS = {
    "vlc_path": "",
    "library_folders": [],
    "watch_order": [],
    "episode_mode": "universal",
    "universal_count": 3,
    "default_episode_count": 3,
    "individual_counts": {},
    "start_mode": "memory",
    "history_limit": 500,
    "sleep_timer_mode": "off",
    "sleep_timer_minutes": 60,
    "theme": "modern",
}


def load_settings():
    data = load_json(paths.SETTINGS_FILE, DEFAULTS.copy())
    if not isinstance(data, dict):
        data = DEFAULTS.copy()
    for key, value in DEFAULTS.items():
        data.setdefault(key, value)

    if not data["library_folders"]:
        legacy = load_json(paths.LEGACY_LIBRARY_FILE, [])
        if isinstance(legacy, list):
            data["library_folders"] = [
                folder for folder in legacy if isinstance(folder, str)
            ]
    return data


def save_settings(data):
    save_json(paths.SETTINGS_FILE, data)