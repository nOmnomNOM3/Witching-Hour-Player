import os
import re

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov")
IGNORED_FOLDERS = {
    "extras",
    "extra",
    "movies",
    "movie",
    "special features",
    "behind the scenes",
    "bonus",
    "bonus features",
    "trailers",
}
WATCH_SEASON_MARKER = " — Season "


def list_subdirectories(folder):
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    result = []
    for name in names:
        if name.lower() in IGNORED_FOLDERS:
            continue
        path = os.path.join(folder, name)
        if os.path.isdir(path):
            result.append((name, path))
    return result


def folder_contains_videos(folder, max_depth=3):
    folder = os.path.abspath(folder)
    try:
        walker = os.walk(folder)
    except OSError:
        return False
    for root, directories, files in walker:
        directories[:] = [
            name for name in directories if name.lower() not in IGNORED_FOLDERS
        ]
        relative = os.path.relpath(root, folder)
        depth = 0 if relative == "." else relative.count(os.sep) + 1
        if depth > max_depth:
            directories.clear()
            continue
        for filename in files:
            if filename.lower().endswith(VIDEO_EXTENSIONS):
                return True
    return False


def season_number_from_name(name):
    text = name.strip()
    match = re.search(r"(?:season|s)\s*[-.]?\s*(\d{1,2})\b", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if re.fullmatch(r"\d{1,2}", text):
        number = int(text)
        if 1 <= number <= 50:
            return number
    return None


def season_children(folder):
    found = []
    for name, path in list_subdirectories(folder):
        number = season_number_from_name(name)
        if number is None:
            continue
        if folder_contains_videos(path):
            found.append((number, path))
    found.sort(key=lambda item: item[0])
    return found


def is_show_folder(folder):
    if folder_contains_videos(folder, max_depth=0):
        return True
    children = list_subdirectories(folder)
    seasons = season_children(folder)
    if not children:
        return folder_contains_videos(folder)
    if seasons and len(seasons) >= max(1, int(len(children) * 0.5)):
        return True
    return False


def parse_watch_entry(entry):
    if not isinstance(entry, str):
        return str(entry), None
    if WATCH_SEASON_MARKER in entry:
        show, season_text = entry.rsplit(WATCH_SEASON_MARKER, 1)
        try:
            return show, int(season_text)
        except ValueError:
            return entry, None
    return entry, None


def format_watch_entry(show, season=None):
    if season is None:
        return show
    return f"{show}{WATCH_SEASON_MARKER}{int(season):02d}"


def find_episodes(show_folder):
    episodes = []
    for root, folders, files in os.walk(show_folder):
        folders[:] = [
            folder for folder in folders if folder.lower() not in IGNORED_FOLDERS
        ]
        folder_name = os.path.basename(root)
        folder_season = season_number_from_name(folder_name)

        for filename in files:
            if not filename.lower().endswith(VIDEO_EXTENSIONS):
                continue
            season_number, episode_number = parse_episode_filename(
                filename, folder_season
            )
            if season_number is None or episode_number is None:
                continue
            episodes.append(
                (season_number, episode_number, os.path.join(root, filename))
            )

    episodes.sort(key=lambda item: (item[0], item[1]))
    if episodes:
        return episodes

    unnumbered = []
    for root, folders, files in os.walk(show_folder):
        folders[:] = [
            folder for folder in folders if folder.lower() not in IGNORED_FOLDERS
        ]
        for filename in files:
            if filename.lower().endswith(VIDEO_EXTENSIONS):
                unnumbered.append(os.path.join(root, filename))
    unnumbered.sort(key=lambda path: os.path.basename(path).lower())
    return [(1, index, path) for index, path in enumerate(unnumbered, start=1)]


def parse_episode_filename(filename, folder_season):
    patterns = [
        (r"\bS\s*(\d+)\s*[-.]?\s*E\s*(\d+)\b", True),
        (r"\bSeason\s*(\d+)\s+Episode\s*(\d+)\b", True),
        (r"\bEpisode\s*(\d+)\b", False),
        (r"\bEp\.?\s*(\d+)\b", False),
        (r"\bE(\d+)\b", False),
        (r"\b(\d+)\s*-\s*(\d+)\b", True),
        (r"-\s*(\d{1,3})\s*-", False),
        (r"-\s*(\d{1,3})(?:\s*\[|\s*$)", False),
        (r"\.(\d{1,3})\.", False),
        (r"_(\d+)(?:\D|$)", False),
    ]
    fallback = folder_season if folder_season is not None else 1
    for pattern, has_season in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if not match:
            continue
        if has_season and match.lastindex >= 2:
            return int(match.group(1)), int(match.group(2))
        return fallback, int(match.group(1))
    return None, None


class Library:
    def __init__(self):
        self.shows = []
        self.paths = {}
        self.seasons = {}

    def _register(self, folder):
        name = os.path.basename(folder)
        if name in self.paths:
            parent = os.path.basename(os.path.dirname(folder))
            name = f"{name} [{parent}]"
            original = name
            counter = 2
            while name in self.paths:
                name = f"{original} {counter}"
                counter += 1
        self.paths[name] = folder
        self.seasons[name] = [number for number, _path in season_children(folder)]
        self.shows.append(name)

    def _discover(self, folder, depth=0, max_depth=4):
        if depth > max_depth:
            return
        seasons = season_children(folder)
        children = list_subdirectories(folder)
        if len(seasons) >= 2:
            self._register(folder)
            return
        if is_show_folder(folder):
            self._register(folder)
            return
        if len(seasons) == 1 and len(children) == 1:
            self._register(folder)
            return
        for _name, child in children:
            self._discover(child, depth + 1, max_depth)

    def scan(self, library_folders):
        self.shows = []
        self.paths = {}
        self.seasons = {}
        for root in library_folders:
            if not os.path.isdir(root):
                continue
            if is_show_folder(root) or len(season_children(root)) >= 2:
                self._register(root)
                continue
            for _name, child in list_subdirectories(root):
                self._discover(child)
        self.shows.sort(key=str.lower)
        return self.shows

    def seasons_for(self, show):
        known = list(self.seasons.get(show, []))
        if known:
            return known
        folder = self.paths.get(show)
        if not folder:
            return []
        detected = sorted({episode[0] for episode in find_episodes(folder)})
        self.seasons[show] = detected
        return detected
