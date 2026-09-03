import os
from datetime import datetime

from . import paths
from .store import delete_file, load_json, save_json


class Memory:
    def __init__(self):
        data = load_json(paths.MEMORY_FILE, {})
        self.data = data if isinstance(data, dict) else {}
        session = load_json(paths.SESSION_FILE, {})
        self.session = session if isinstance(session, dict) else {}

    def save(self):
        save_json(paths.MEMORY_FILE, self.data)

    def set_episode(self, show, season, episode, resume_time=0, path=None):
        entry = {
            "season": int(season),
            "episode": int(episode),
            "resume_time": max(0, int(resume_time)),
        }
        if path:
            entry["path"] = path
        self.data[show] = entry
        self.save()

    def advance(self, item):
        show = item.get("show")
        if not show:
            return
        nxt_season = item.get("next_season")
        nxt_episode = item.get("next_episode")
        if nxt_season is None or nxt_episode is None:
            return
        self.set_episode(show, nxt_season, nxt_episode, 0)

    def interrupt(self, item, seconds):
        show = item.get("show")
        if not show:
            return
        self.set_episode(
            show,
            item.get("season", 1),
            item.get("episode", 1),
            max(0, int(seconds)),
            item.get("path"),
        )

    def starting_index(self, show, episodes, start_mode):
        if not episodes:
            return 0
        if start_mode == "random":
            import random

            return random.randint(0, len(episodes) - 1)
        saved = self.data.get(show)
        if not isinstance(saved, dict):
            import random

            return random.randint(0, len(episodes) - 1)
        season = saved.get("season")
        episode = saved.get("episode")
        for index, item in enumerate(episodes):
            if item[0] == season and item[1] == episode:
                return index
        return 0

    def resume_time(self, show, episode, start_mode):
        if start_mode != "memory":
            return 0
        saved = self.data.get(show)
        if not isinstance(saved, dict):
            return 0
        if saved.get("season") == episode[0] and saved.get("episode") == episode[1]:
            try:
                return max(0, int(saved.get("resume_time", 0)))
            except (TypeError, ValueError):
                return 0
        return 0

    def save_session(self, items, index=0, current_time=0):
        self.session = {
            "items": items,
            "current_index": index,
            "current_time": int(current_time),
            "updated": datetime.now().isoformat(timespec="seconds"),
        }
        save_json(paths.SESSION_FILE, self.session)

    def clear_session(self):
        self.session = {}
        delete_file(paths.SESSION_FILE)

    def load_history(self, limit=500):
        data = load_json(paths.HISTORY_FILE, [])
        if not isinstance(data, list):
            return []
        return data[-limit:]

    def record_play(self, item, limit=500):
        if not item:
            return
        path = item.get("path") or ""
        history = self.load_history(limit)
        if history and history[-1].get("path") == path:
            return
        history.append(
            {
                "when": datetime.now().isoformat(timespec="seconds"),
                "show": item.get("show", ""),
                "season": item.get("season"),
                "episode": item.get("episode"),
                "path": path,
            }
        )
        save_json(paths.HISTORY_FILE, history[-limit:])

    def valid_session(self):
        items = self.session.get("items", [])
        if not isinstance(items, list) or not items:
            return False
        index = self.session.get("current_index", 0)
        if not isinstance(index, int) or index < 0 or index >= len(items):
            return False
        path = items[index].get("path")
        return bool(path) and os.path.exists(path)