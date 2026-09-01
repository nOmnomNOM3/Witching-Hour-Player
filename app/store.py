import json
import os


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError, TypeError):
        return default


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)
    except OSError:
        pass


def delete_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
