from .library import find_episodes, parse_watch_entry


def build_playlist(watch_order, library, memory, settings, universal_count):
    items = []
    mode = settings.get("episode_mode", "universal")
    start_mode = settings.get("start_mode", "memory")
    individual = settings.get("individual_counts", {})

    for entry in watch_order:
        show, season_filter = parse_watch_entry(entry)
        folder = library.paths.get(show)
        if not folder:
            continue
        episodes = find_episodes(folder)
        if season_filter is not None:
            episodes = [ep for ep in episodes if ep[0] == season_filter]
        if not episodes:
            continue

        if mode == "universal":
            count = max(1, int(universal_count))
        else:
            count = int(individual.get(entry, individual.get(show, 3)))
            count = max(1, count)

        if len(episodes) < count:
            continue

        start = memory.starting_index(show, episodes, start_mode)
        for offset in range(count):
            index = (start + offset) % len(episodes)
            episode = episodes[index]
            nxt = episodes[(index + 1) % len(episodes)]
            items.append(
                {
                    "show": show,
                    "season": episode[0],
                    "episode": episode[1],
                    "path": episode[2],
                    "resume_time": memory.resume_time(show, episode, start_mode),
                    "next_season": nxt[0],
                    "next_episode": nxt[1],
                }
            )
    return items


def remaining_session_items(session):
    items = session.get("items", [])
    index = session.get("current_index", 0)
    current_time = session.get("current_time", 0)
    remaining = []
    for offset, item in enumerate(items[index:], start=index):
        path = item.get("path", "")
        if not path:
            continue
        copy = item.copy()
        if offset == index:
            try:
                copy["resume_time"] = max(0, int(current_time))
            except (TypeError, ValueError):
                copy["resume_time"] = 0
        remaining.append(copy)
    return remaining
