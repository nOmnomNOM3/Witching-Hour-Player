import tkinter as tk
from tkinter import filedialog, messagebox

import os
import re
import random
import subprocess
import json


# ==================================================
# WITCHING HOUR
# ==================================================


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"

program_folder = os.path.dirname(
    os.path.abspath(__file__)
)

memory_file = os.path.join(
    program_folder,
    "playback_memory.json"
)

library_file = os.path.join(
    program_folder,
    "library_folders.json"
)


# --------------------------------------------------
# PLAYBACK MEMORY
# --------------------------------------------------

def load_memory():

    if not os.path.exists(memory_file):
        return {}

    try:

        with open(
            memory_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return {}


def save_memory():

    try:

        with open(
            memory_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                playback_memory,
                file,
                indent=4
            )

    except OSError:

        pass


playback_memory = load_memory()


# --------------------------------------------------
# LIBRARY FOLDER SETTINGS
# --------------------------------------------------

def load_library_folders():

    if not os.path.exists(library_file):
        return []

    try:

        with open(
            library_file,
            "r",
            encoding="utf-8"
        ) as file:

            folders = json.load(file)

        if not isinstance(folders, list):
            return []

        return [
            folder
            for folder in folders
            if isinstance(folder, str)
            and os.path.isdir(folder)
        ]

    except (json.JSONDecodeError, OSError):

        return []


def save_library_folders():

    try:

        with open(
            library_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                library_folders,
                file,
                indent=4
            )

    except OSError:

        pass


library_folders = load_library_folders()


# --------------------------------------------------
# SHOW LIBRARY
# --------------------------------------------------

shows = []

show_paths = {}


def scan_library():

    global shows
    global show_paths

    shows = []
    show_paths = {}

    for library_folder in library_folders:

        if not os.path.isdir(library_folder):
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

            if not os.path.isdir(item_path):
                continue

            display_name = item

            # ------------------------------------------
            # HANDLE DUPLICATE SHOW NAMES
            # ------------------------------------------

            if display_name in show_paths:

                parent_name = os.path.basename(
                    library_folder
                )

                display_name = (
                    f"{item} [{parent_name}]"
                )

                counter = 2

                original_name = display_name

                while display_name in show_paths:

                    display_name = (
                        f"{original_name} {counter}"
                    )

                    counter += 1

            show_paths[display_name] = item_path

            shows.append(
                display_name
            )

    shows.sort(
        key=str.lower
    )


# --------------------------------------------------
# FIND EPISODES
# --------------------------------------------------

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
            if folder.lower() not in ignored_folders
        ]

        folder_name = os.path.basename(
            root
        )

        # ----------------------------------------------
        # FIND SEASON FROM FOLDER NAME
        # ----------------------------------------------

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

        # ----------------------------------------------
        # CHECK VIDEO FILES
        # ----------------------------------------------

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

            # ------------------------------------------
            # S01E01 / S01 E01 / S01 - E01
            # ------------------------------------------

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

                # --------------------------------------
                # Season 1 Episode 04
                # --------------------------------------

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

                    # ----------------------------------
                    # Episode 05
                    # ----------------------------------

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

                        # ------------------------------
                        # Ep.05 / Ep 05
                        # ------------------------------

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

                            # --------------------------
                            # E01 / e02
                            # --------------------------

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

                                # ----------------------
                                # 1-05
                                # ----------------------

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

                                    # ------------------
                                    # - 004 -
                                    # ------------------

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
                                            if folder_season
                                            is not None
                                            else 1
                                        )

                                    else:

                                        # --------------
                                        # - 01 [720p]
                                        # --------------

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
                                                if folder_season
                                                is not None
                                                else 1
                                            )

                                        else:

                                            # ----------
                                            # .02.
                                            # ----------

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
                                                    if folder_season
                                                    is not None
                                                    else 1
                                                )

                                            else:

                                                # ------
                                                # _05
                                                # ------

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
                                                        if folder_season
                                                        is not None
                                                        else 1
                                                    )

            # ------------------------------------------
            # SAVE NUMBERED EPISODE
            # ------------------------------------------

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

    # --------------------------------------------------
    # SORT NUMBERED EPISODES
    # --------------------------------------------------

    episodes.sort(
        key=lambda x: (
            x[0],
            x[1]
        )
    )

    # --------------------------------------------------
    # FALLBACK FOR UNNUMBERED SHOWS
    # --------------------------------------------------

    if not episodes:

        unnumbered_files = []

        for root, folders, files in os.walk(
            show_folder
        ):

            folders[:] = [
                folder
                for folder in folders
                if folder.lower() not in ignored_folders
            ]

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

                unnumbered_files.append(
                    os.path.join(
                        root,
                        filename
                    )
                )

        unnumbered_files.sort(
            key=lambda path:
            os.path.basename(path).lower()
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


# --------------------------------------------------
# STARTING EPISODE MODE
# --------------------------------------------------

start_mode = "memory"


def get_starting_index(
    show,
    episodes
):

    # --------------------------------------------------
    # RANDOM MODE
    # --------------------------------------------------

    if start_mode == "random":

        return random.randint(
            0,
            len(episodes) - 1
        )

    # --------------------------------------------------
    # MEMORY MODE
    # --------------------------------------------------

    if show not in playback_memory:

        return random.randint(
            0,
            len(episodes) - 1
        )

    try:

        saved_season = playback_memory[
            show
        ]["season"]

        saved_episode = playback_memory[
            show
        ]["episode"]

    except (
        KeyError,
        TypeError
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


# --------------------------------------------------
# SAVE NEXT EPISODE
# --------------------------------------------------

def save_next_episode(
    show,
    episodes,
    next_index
):

    if next_index >= len(episodes):

        next_index = 0

    next_episode = episodes[
        next_index
    ]

    playback_memory[show] = {
        "season": next_episode[0],
        "episode": next_episode[1]
    }

    save_memory()


# --------------------------------------------------
# WATCH ORDER DATA
# --------------------------------------------------

watch_order = []


# --------------------------------------------------
# ADD TO WATCH ORDER
# --------------------------------------------------

def add_to_watch_order():

    selected_indices = show_list.curselection()

    if not selected_indices:

        status_label.config(
            text="Select a show first."
        )

        return

    added = 0

    for index in selected_indices:

        show = shows[index]

        if show not in watch_order:

            watch_order.append(
                show
            )

            order_list.insert(
                tk.END,
                show
            )

            added += 1

    if added:

        status_label.config(
            text="Show added to watch order."
        )

    else:

        status_label.config(
            text="Selected show is already in the watch order."
        )


# --------------------------------------------------
# REMOVE FROM WATCH ORDER
# --------------------------------------------------

def remove_from_watch_order():

    selected_indices = order_list.curselection()

    if not selected_indices:

        status_label.config(
            text="Select a show from the watch order first."
        )

        return

    index = selected_indices[0]

    removed_show = watch_order[
        index
    ]

    order_list.delete(
        index
    )

    del watch_order[
        index
    ]

    individual_counts.pop(
        removed_show,
        None
    )

    update_individual_controls()

    status_label.config(
        text="Show removed from watch order."
    )


# --------------------------------------------------
# MOVE UP
# --------------------------------------------------

def move_up():

    selected_indices = order_list.curselection()

    if not selected_indices:
        return

    index = selected_indices[0]

    if index == 0:
        return

    watch_order[
        index
    ], watch_order[
        index - 1
    ] = (
        watch_order[index - 1],
        watch_order[index]
    )

    refresh_watch_order(
        index - 1
    )


# --------------------------------------------------
# MOVE DOWN
# --------------------------------------------------

def move_down():

    selected_indices = order_list.curselection()

    if not selected_indices:
        return

    index = selected_indices[0]

    if index >= len(watch_order) - 1:
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


# --------------------------------------------------
# REFRESH WATCH ORDER
# --------------------------------------------------

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

    if selected_index is not None:

        order_list.selection_set(
            selected_index
        )

        order_list.activate(
            selected_index
        )

        order_list.see(
            selected_index
        )

    update_individual_controls()


# --------------------------------------------------
# CLEAR WATCH ORDER
# --------------------------------------------------

def clear_watch_order():

    watch_order.clear()

    order_list.delete(
        0,
        tk.END
    )

    update_individual_controls()

    status_label.config(
        text="Watch order cleared."
    )


# --------------------------------------------------
# EPISODE COUNT MODE
# --------------------------------------------------

episode_mode = "universal"

individual_counts = {}


def change_episode_mode():

    global episode_mode

    episode_mode = mode_var.get()

    update_individual_controls()

    if episode_mode == "universal":

        status_label.config(
            text="Universal episode count selected."
        )

    else:

        status_label.config(
            text=(
                "Select a show in Watch Order "
                "to set its episode count."
            )
        )


# --------------------------------------------------
# UPDATE INDIVIDUAL CONTROLS
# --------------------------------------------------

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

    selected_indices = order_list.curselection()

    if not selected_indices:

        individual_label.config(
            text="Select a show from Watch Order."
        )

        individual_entry.delete(
            0,
            tk.END
        )

        return

    index = selected_indices[0]

    show = watch_order[index]

    current_count = individual_counts.get(
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
        str(current_count)
    )


# --------------------------------------------------
# SAVE INDIVIDUAL COUNT
# --------------------------------------------------

def save_individual_count():

    if episode_mode != "individual":

        status_label.config(
            text="Switch to Individual mode first."
        )

        return

    selected_indices = order_list.curselection()

    if not selected_indices:

        status_label.config(
            text="Select a show from Watch Order first."
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
            text="Please enter a valid episode count."
        )

        return

    index = selected_indices[0]

    show = watch_order[index]

    individual_counts[
        show
    ] = count

    status_label.config(
        text=f"{show} set to {count} episode(s)."
    )


# --------------------------------------------------
# WATCH ORDER SELECTION
# --------------------------------------------------

def watch_order_selected(
    event=None
):

    update_individual_controls()


# --------------------------------------------------
# CHANGE START MODE
# --------------------------------------------------

def change_start_mode():

    global start_mode

    start_mode = start_mode_var.get()

    if start_mode == "memory":

        status_label.config(
            text="Playback will continue from memory."
        )

    else:

        status_label.config(
            text="A random starting episode will be selected."
        )


# --------------------------------------------------
# REFRESH AVAILABLE SHOWS
# --------------------------------------------------

def refresh_available_shows():

    scan_library()

    show_list.delete(
        0,
        tk.END
    )

    for show in shows:

        show_list.insert(
            tk.END,
            f"  {show}"
        )

    # Remove watch-order entries whose folders
    # no longer exist in the configured libraries.

    removed = False

    for show in watch_order[:]:

        if show not in show_paths:

            watch_order.remove(
                show
            )

            individual_counts.pop(
                show,
                None
            )

            removed = True

    if removed:

        refresh_watch_order()

    if not library_folders:

        status_label.config(
            text="No library folders have been selected."
        )

    elif not shows:

        status_label.config(
            text="No shows found. Check your library folders."
        )

    else:

        status_label.config(
            text=f"Found {len(shows)} show(s)."
        )


# --------------------------------------------------
# ADD LIBRARY FOLDER
# --------------------------------------------------

def add_library_folder():

    folder = filedialog.askdirectory(
        title="Choose a TV Library Folder"
    )

    if not folder:
        return

    folder = os.path.normpath(
        folder
    )

    existing_normalized = [
        os.path.normcase(
            os.path.normpath(
                existing
            )
        )
        for existing in library_folders
    ]

    if (
        os.path.normcase(folder)
        in existing_normalized
    ):

        messagebox.showinfo(
            "Witching Hour",
            "That folder is already in your library."
        )

        return

    library_folders.append(
        folder
    )

    save_library_folders()

    refresh_available_shows()

    status_label.config(
        text=f"Added library: {folder}"
    )


# --------------------------------------------------
# MANAGE LIBRARY FOLDERS
# --------------------------------------------------

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

    manager.minsize(
        650,
        350
    )

    manager.configure(
        bg=BLACK
    )

    manager.transient(
        window
    )

    title_label = tk.Label(
        manager,
        text="🎃  LIBRARY FOLDERS",
        font=(
            "Arial",
            18,
            "bold"
        ),
        bg=BLACK,
        fg=ORANGE
    )

    title_label.pack(
        pady=(
            20,
            5
        )
    )

    info_label = tk.Label(
        manager,
        text=(
            "Witching Hour scans these locations "
            "for television shows."
        ),
        font=(
            "Arial",
            10
        ),
        bg=BLACK,
        fg=WHITE
    )

    info_label.pack(
        pady=(
            0,
            15
        )
    )

    list_frame = tk.Frame(
        manager,
        bg=ORANGE
    )

    list_frame.pack(
        fill=tk.BOTH,
        expand=True,
        padx=20,
        pady=10
    )

    folder_list = tk.Listbox(
        list_frame,
        font=(
            "Arial",
            11
        ),
        bg=DARK_BLACK,
        fg=WHITE,
        selectbackground=ORANGE,
        selectforeground=BLACK,
        activestyle="none",
        highlightthickness=0,
        relief=tk.FLAT,
        borderwidth=0
    )

    folder_scrollbar = tk.Scrollbar(
        list_frame,
        command=folder_list.yview
    )

    folder_list.config(
        yscrollcommand=folder_scrollbar.set
    )

    folder_scrollbar.pack(
        side=tk.RIGHT,
        fill=tk.Y
    )

    folder_list.pack(
        side=tk.LEFT,
        fill=tk.BOTH,
        expand=True,
        padx=1,
        pady=1
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

        existing_normalized = [
            os.path.normcase(
                os.path.normpath(
                    existing
                )
            )
            for existing in library_folders
        ]

        if (
            os.path.normcase(folder)
            in existing_normalized
        ):

            messagebox.showinfo(
                "Witching Hour",
                "That folder is already in your library.",
                parent=manager
            )

            return

        library_folders.append(
            folder
        )

        save_library_folders()

        refresh_folder_list()

        refresh_available_shows()

    def manager_remove():

        selected = folder_list.curselection()

        if not selected:

            messagebox.showinfo(
                "Witching Hour",
                "Select a folder to remove.",
                parent=manager
            )

            return

        index = selected[0]

        folder = library_folders[
            index
        ]

        confirmed = messagebox.askyesno(
            "Remove Library Folder?",
            (
                "Stop scanning this folder?\n\n"
                f"{folder}\n\n"
                "No video files will be deleted."
            ),
            parent=manager
        )

        if not confirmed:
            return

        del library_folders[
            index
        ]

        save_library_folders()

        refresh_folder_list()

        refresh_available_shows()

    button_frame = tk.Frame(
        manager,
        bg=BLACK
    )

    button_frame.pack(
        pady=(
            5,
            20
        )
    )

    add_button = tk.Button(
        button_frame,
        text="ADD FOLDER",
        command=manager_add,
        bg=ORANGE,
        fg=BLACK,
        activebackground=GOLD,
        activeforeground=BLACK,
        font=(
            "Arial",
            10,
            "bold"
        ),
        relief=tk.FLAT,
        padx=15,
        pady=7,
        cursor="hand2"
    )

    add_button.pack(
        side=tk.LEFT,
        padx=5
    )

    remove_button = tk.Button(
        button_frame,
        text="REMOVE SELECTED",
        command=manager_remove,
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
        padx=15,
        pady=7,
        cursor="hand2"
    )

    remove_button.pack(
        side=tk.LEFT,
        padx=5
    )

    done_button = tk.Button(
        button_frame,
        text="DONE",
        command=manager.destroy,
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
        padx=15,
        pady=7,
        cursor="hand2"
    )

    done_button.pack(
        side=tk.LEFT,
        padx=5
    )

    refresh_folder_list()


# --------------------------------------------------
# FIRST-LAUNCH LIBRARY SETUP
# --------------------------------------------------

def first_launch_library_setup():

    if library_folders:
        return

    messagebox.showinfo(
        "Welcome to Witching Hour",
        (
            "Welcome to Witching Hour! 🎃\n\n"
            "First, choose the folder that contains "
            "your television shows.\n\n"
            "Each folder inside that location will "
            "be treated as a show.\n\n"
            "You can add more library locations too."
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
                "Would you like to add another "
                "TV library folder?"
            )
        )

        if not another:
            break

    save_library_folders()


# --------------------------------------------------
# START PLAYBACK
# --------------------------------------------------

def start_playback():

    if not watch_order:

        status_label.config(
            text="Add at least one show to the watch order."
        )

        return

    if not os.path.exists(
        vlc_path
    ):

        messagebox.showerror(
            "VLC Not Found",
            (
                "Witching Hour could not find VLC at:\n\n"
                f"{vlc_path}\n\n"
                "VLC must be installed before playback."
            )
        )

        return

    # --------------------------------------------------
    # UNIVERSAL EPISODE COUNT
    # --------------------------------------------------

    if episode_mode == "universal":

        try:

            universal_count = int(
                episode_entry.get()
            )

            if universal_count < 1:
                raise ValueError

        except ValueError:

            status_label.config(
                text="Please enter a valid episode count."
            )

            return

    # --------------------------------------------------
    # SAVE CURRENT INDIVIDUAL VALUE
    # --------------------------------------------------

    if episode_mode == "individual":

        selected_indices = order_list.curselection()

        if selected_indices:

            try:

                count = int(
                    individual_entry.get()
                )

                if count < 1:
                    raise ValueError

                selected_show = watch_order[
                    selected_indices[0]
                ]

                individual_counts[
                    selected_show
                ] = count

            except ValueError:

                status_label.config(
                    text="Please enter a valid episode count."
                )

                return

    all_selected_episodes = []

    # --------------------------------------------------
    # PROCESS SHOWS
    # --------------------------------------------------

    for show in watch_order:

        show_folder = show_paths.get(
            show
        )

        if not show_folder:

            status_label.config(
                text=(
                    f"Library folder for {show} "
                    "could not be found."
                )
            )

            continue

        episodes = find_episodes(
            show_folder
        )

        if not episodes:

            status_label.config(
                text=f"No episodes found in {show}."
            )

            continue

        # --------------------------------------------------
        # EPISODE COUNT
        # --------------------------------------------------

        if episode_mode == "universal":

            number_of_episodes = universal_count

        else:

            number_of_episodes = individual_counts.get(
                show,
                3
            )

        # We intentionally allow wrap-around,
        # even if requested count exceeds the library.

        start = get_starting_index(
            show,
            episodes
        )

        selected_episodes = []

        for offset in range(
            number_of_episodes
        ):

            index = (
                start + offset
            ) % len(episodes)

            selected_episodes.append(
                episodes[index]
            )

        all_selected_episodes.extend(
            selected_episodes
        )

        next_index = (
            start + number_of_episodes
        ) % len(episodes)

        save_next_episode(
            show,
            episodes,
            next_index
        )

    # --------------------------------------------------
    # VERIFY PLAYLIST
    # --------------------------------------------------

    if not all_selected_episodes:

        status_label.config(
            text="No episodes could be selected."
        )

        return

    episode_paths = [
        episode[2]
        for episode in all_selected_episodes
    ]

    # --------------------------------------------------
    # START VLC
    # --------------------------------------------------

    try:

        subprocess.Popen(
            [vlc_path] + episode_paths
        )

        status_label.config(
            text=(
                f"Playback started — "
                f"{len(episode_paths)} episode(s)."
            )
        )

    except OSError as error:

        messagebox.showerror(
            "Playback Error",
            (
                "Witching Hour could not start VLC.\n\n"
                f"{error}"
            )
        )


# ==================================================
# GUI
# ==================================================

window = tk.Tk()

window.title(
    "🎃 Witching Hour"
)

window.geometry(
    "1100x920"
)

window.minsize(
    1000,
    820
)


# --------------------------------------------------
# HALLOWEEN COLOR PALETTE
# --------------------------------------------------

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


# --------------------------------------------------
# BUTTON HELPER
# --------------------------------------------------

def halloween_button(
    parent,
    text,
    command,
    width=None,
    big=False
):

    if big:

        font = (
            "Arial",
            15,
            "bold"
        )

        pady = 10

    else:

        font = (
            "Arial",
            10,
            "bold"
        )

        pady = 6

    button = tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        font=font,
        bg=DARK_BLACK,
        fg=ORANGE,
        activebackground=ORANGE,
        activeforeground=BLACK,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=1,
        highlightbackground=DARK_ORANGE,
        highlightcolor=ORANGE,
        cursor="hand2",
        padx=10,
        pady=pady
    )

    return button


# --------------------------------------------------
# MENU BAR
# --------------------------------------------------

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

file_menu.add_separator()

file_menu.add_command(
    label="Rescan Library",
    command=refresh_available_shows
)

file_menu.add_separator()

file_menu.add_command(
    label="Exit",
    command=window.destroy
)

menu_bar.add_cascade(
    label="File",
    menu=file_menu
)

window.config(
    menu=menu_bar
)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

header_frame = tk.Frame(
    window,
    bg=BLACK
)

header_frame.pack(
    fill=tk.X,
    padx=25,
    pady=(
        18,
        5
    )
)


pumpkin_left = tk.Label(
    header_frame,
    text="🎃",
    font=(
        "Segoe UI Emoji",
        28
    ),
    bg=BLACK,
    fg=ORANGE
)

pumpkin_left.pack(
    side=tk.LEFT,
    padx=(
        10,
        15
    )
)


title = tk.Label(
    header_frame,
    text="WITCHING HOUR",
    font=(
        "Arial",
        26,
        "bold"
    ),
    bg=BLACK,
    fg=ORANGE
)

title.pack(
    side=tk.LEFT,
    expand=True
)


pumpkin_right = tk.Label(
    header_frame,
    text="🎃",
    font=(
        "Segoe UI Emoji",
        28
    ),
    bg=BLACK,
    fg=ORANGE
)

pumpkin_right.pack(
    side=tk.RIGHT,
    padx=(
        15,
        10
    )
)


subtitle = tk.Label(
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
)

subtitle.pack(
    pady=(
        0,
        10
    )
)


orange_line = tk.Frame(
    window,
    bg=ORANGE,
    height=2
)

orange_line.pack(
    fill=tk.X,
    padx=55,
    pady=(
        0,
        15
    )
)


# --------------------------------------------------
# MAIN CONTENT
# --------------------------------------------------

main_frame = tk.Frame(
    window,
    bg=BLACK
)

main_frame.pack(
    fill=tk.BOTH,
    expand=True,
    padx=25
)


# --------------------------------------------------
# AVAILABLE SHOWS
# --------------------------------------------------

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
        10
    )
)


available_header = tk.Frame(
    available_frame,
    bg=PANEL_BLACK
)

available_header.pack(
    fill=tk.X,
    padx=12,
    pady=(
        10,
        4
    )
)


available_label = tk.Label(
    available_header,
    text="🎃  AVAILABLE SHOWS",
    font=(
        "Arial",
        14,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
)

available_label.pack(
    side=tk.LEFT
)


available_hint = tk.Label(
    available_frame,
    text="Select one or more shows",
    font=(
        "Arial",
        9
    ),
    bg=PANEL_BLACK,
    fg=LIGHT_GRAY
)

available_hint.pack(
    anchor="w",
    padx=15,
    pady=(
        0,
        8
    )
)


show_list_frame = tk.Frame(
    available_frame,
    bg=ORANGE
)

show_list_frame.pack(
    fill=tk.BOTH,
    expand=True,
    padx=12,
    pady=(
        0,
        12
    )
)


show_list = tk.Listbox(
    show_list_frame,
    selectmode=tk.EXTENDED,
    width=42,
    height=24,
    font=(
        "Arial",
        12
    ),
    activestyle="none",
    bg=DARK_BLACK,
    fg=WHITE,
    selectbackground=ORANGE,
    selectforeground=BLACK,
    highlightthickness=0,
    borderwidth=0,
    relief=tk.FLAT
)


show_scrollbar = tk.Scrollbar(
    show_list_frame,
    command=show_list.yview,
    bg=DARK_BLACK,
    troughcolor=LIGHT_BLACK,
    activebackground=ORANGE
)

show_list.config(
    yscrollcommand=show_scrollbar.set
)

show_scrollbar.pack(
    side=tk.RIGHT,
    fill=tk.Y
)

show_list.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
    padx=1,
    pady=1
)


# --------------------------------------------------
# MIDDLE BUTTONS
# --------------------------------------------------

button_frame = tk.Frame(
    main_frame,
    bg=BLACK
)

button_frame.pack(
    side=tk.LEFT,
    padx=8
)


tk.Label(
    button_frame,
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
        15
    )
)


add_button = halloween_button(
    button_frame,
    "ADD  →",
    add_to_watch_order,
    width=12
)

add_button.pack(
    pady=5
)


remove_button = halloween_button(
    button_frame,
    "←  REMOVE",
    remove_from_watch_order,
    width=12
)

remove_button.pack(
    pady=5
)


up_button = halloween_button(
    button_frame,
    "▲  MOVE UP",
    move_up,
    width=12
)

up_button.pack(
    pady=(
        20,
        5
    )
)


down_button = halloween_button(
    button_frame,
    "▼  MOVE DOWN",
    move_down,
    width=12
)

down_button.pack(
    pady=5
)


clear_button = tk.Button(
    button_frame,
    text="☠  CLEAR",
    font=(
        "Arial",
        10,
        "bold"
    ),
    width=12,
    command=clear_watch_order,
    bg=DARK_PURPLE,
    fg=WHITE,
    activebackground=PURPLE,
    activeforeground=WHITE,
    relief=tk.FLAT,
    bd=0,
    cursor="hand2",
    pady=6
)

clear_button.pack(
    pady=(
        20,
        5
    )
)


# --------------------------------------------------
# WATCH ORDER
# --------------------------------------------------

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
        10,
        0
    )
)


order_label = tk.Label(
    order_frame,
    text="👻  WATCH ORDER",
    font=(
        "Arial",
        14,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
)

order_label.pack(
    anchor="w",
    padx=12,
    pady=(
        10,
        4
    )
)


order_hint = tk.Label(
    order_frame,
    text="Episodes will play in this order",
    font=(
        "Arial",
        9
    ),
    bg=PANEL_BLACK,
    fg=LIGHT_GRAY
)

order_hint.pack(
    anchor="w",
    padx=15,
    pady=(
        0,
        8
    )
)


order_list_frame = tk.Frame(
    order_frame,
    bg=ORANGE
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
    width=42,
    height=24,
    font=(
        "Arial",
        12
    ),
    activestyle="none",
    bg=DARK_BLACK,
    fg=WHITE,
    selectbackground=PURPLE,
    selectforeground=WHITE,
    highlightthickness=0,
    borderwidth=0,
    relief=tk.FLAT
)


order_scrollbar = tk.Scrollbar(
    order_list_frame,
    command=order_list.yview,
    bg=DARK_BLACK,
    troughcolor=LIGHT_BLACK,
    activebackground=ORANGE
)

order_list.config(
    yscrollcommand=order_scrollbar.set
)

order_scrollbar.pack(
    side=tk.RIGHT,
    fill=tk.Y
)

order_list.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
    padx=1,
    pady=1
)

order_list.bind(
    "<<ListboxSelect>>",
    watch_order_selected
)


# --------------------------------------------------
# OPTIONS AREA
# --------------------------------------------------

options_frame = tk.Frame(
    window,
    bg=BLACK
)

options_frame.pack(
    fill=tk.X,
    padx=25,
    pady=(
        15,
        5
    )
)


# --------------------------------------------------
# EPISODE COUNT PANEL
# --------------------------------------------------

episode_options_panel = tk.Frame(
    options_frame,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE
)

episode_options_panel.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True,
    padx=(
        0,
        8
    )
)


episode_options_title = tk.Label(
    episode_options_panel,
    text="🎃  EPISODE COUNT",
    font=(
        "Arial",
        13,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
)

episode_options_title.pack(
    pady=(
        10,
        5
    )
)


mode_frame = tk.Frame(
    episode_options_panel,
    bg=PANEL_BLACK
)

mode_frame.pack(
    pady=5
)


mode_var = tk.StringVar(
    value="universal"
)


universal_radio = tk.Radiobutton(
    mode_frame,
    text="Universal",
    variable=mode_var,
    value="universal",
    command=change_episode_mode,
    font=(
        "Arial",
        11,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=ORANGE,
    selectcolor=DARK_BLACK
)

universal_radio.pack(
    side=tk.LEFT,
    padx=12
)


individual_radio = tk.Radiobutton(
    mode_frame,
    text="Individual",
    variable=mode_var,
    value="individual",
    command=change_episode_mode,
    font=(
        "Arial",
        11,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=PURPLE,
    selectcolor=DARK_BLACK
)

individual_radio.pack(
    side=tk.LEFT,
    padx=12
)


# --------------------------------------------------
# UNIVERSAL COUNT
# --------------------------------------------------

episode_frame = tk.Frame(
    episode_options_panel,
    bg=PANEL_BLACK
)

episode_frame.pack(
    pady=5
)


episode_label = tk.Label(
    episode_frame,
    text="Episodes per show:",
    font=(
        "Arial",
        10
    ),
    bg=PANEL_BLACK,
    fg=LIGHT_GRAY
)

episode_label.pack(
    side=tk.LEFT,
    padx=5
)


episode_entry = tk.Entry(
    episode_frame,
    width=5,
    font=(
        "Arial",
        12,
        "bold"
    ),
    justify="center",
    bg=DARK_BLACK,
    fg=GOLD,
    insertbackground=WHITE,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE,
    highlightcolor=ORANGE,
    relief=tk.FLAT
)

episode_entry.insert(
    0,
    "3"
)

episode_entry.pack(
    side=tk.LEFT,
    padx=5
)


# --------------------------------------------------
# INDIVIDUAL COUNT
# --------------------------------------------------

individual_frame = tk.Frame(
    episode_options_panel,
    bg=PANEL_BLACK
)

individual_frame.pack(
    pady=(
        5,
        12
    )
)


individual_label = tk.Label(
    individual_frame,
    text="Individual mode is off.",
    font=(
        "Arial",
        9
    ),
    bg=PANEL_BLACK,
    fg=GRAY
)

individual_label.pack(
    side=tk.LEFT,
    padx=5
)


individual_entry = tk.Entry(
    individual_frame,
    width=5,
    font=(
        "Arial",
        11,
        "bold"
    ),
    justify="center",
    bg=DARK_BLACK,
    fg=GOLD,
    insertbackground=WHITE,
    highlightthickness=1,
    highlightbackground=DARK_ORANGE,
    highlightcolor=ORANGE,
    relief=tk.FLAT
)

individual_entry.pack(
    side=tk.LEFT,
    padx=5
)


individual_save_button = halloween_button(
    individual_frame,
    "SAVE",
    save_individual_count
)

individual_save_button.pack(
    side=tk.LEFT,
    padx=5
)


# --------------------------------------------------
# STARTING EPISODE PANEL
# --------------------------------------------------

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


start_title = tk.Label(
    start_panel,
    text="🎲  STARTING EPISODE",
    font=(
        "Arial",
        13,
        "bold"
    ),
    bg=PANEL_BLACK,
    fg=WHITE
)

start_title.pack(
    pady=(
        10,
        8
    )
)


start_mode_var = tk.StringVar(
    value="memory"
)


memory_radio = tk.Radiobutton(
    start_panel,
    text="🧠  Continue from Memory",
    variable=start_mode_var,
    value="memory",
    command=change_start_mode,
    font=(
        "Arial",
        11
    ),
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=ORANGE,
    selectcolor=DARK_BLACK
)

memory_radio.pack(
    anchor="w",
    padx=30,
    pady=4
)


random_radio = tk.Radiobutton(
    start_panel,
    text="🎲  Random Starting Episode",
    variable=start_mode_var,
    value="random",
    command=change_start_mode,
    font=(
        "Arial",
        11
    ),
    bg=PANEL_BLACK,
    fg=WHITE,
    activebackground=PANEL_BLACK,
    activeforeground=PURPLE,
    selectcolor=DARK_BLACK
)

random_radio.pack(
    anchor="w",
    padx=30,
    pady=(
        4,
        12
    )
)


# --------------------------------------------------
# START BUTTON
# --------------------------------------------------

start_button_frame = tk.Frame(
    window,
    bg=BLACK
)

start_button_frame.pack(
    pady=(
        12,
        8
    )
)


start_button = tk.Button(
    start_button_frame,
    text="▶   START PLAYBACK   🎃",
    font=(
        "Arial",
        17,
        "bold"
    ),
    command=start_playback,
    bg=ORANGE,
    fg=BLACK,
    activebackground=GOLD,
    activeforeground=BLACK,
    relief=tk.FLAT,
    bd=0,
    cursor="hand2",
    padx=35,
    pady=12,
    highlightthickness=2,
    highlightbackground=DARK_ORANGE
)

start_button.pack()


# --------------------------------------------------
# STATUS BAR
# --------------------------------------------------

status_frame = tk.Frame(
    window,
    bg=PANEL_BLACK,
    highlightthickness=1,
    highlightbackground=DARK_PURPLE
)

status_frame.pack(
    fill=tk.X,
    padx=25,
    pady=(
        8,
        18
    )
)


status_icon = tk.Label(
    status_frame,
    text="🎃",
    font=(
        "Segoe UI Emoji",
        13
    ),
    bg=PANEL_BLACK,
    fg=ORANGE
)

status_icon.pack(
    side=tk.LEFT,
    padx=(
        12,
        6
    ),
    pady=7
)


status_label = tk.Label(
    status_frame,
    text="Ready.",
    font=(
        "Arial",
        10
    ),
    bg=PANEL_BLACK,
    fg=WHITE
)

status_label.pack(
    side=tk.LEFT,
    pady=7
)


# --------------------------------------------------
# FIRST-LAUNCH LIBRARY SETUP
# --------------------------------------------------

first_launch_library_setup()

refresh_available_shows()


# --------------------------------------------------
# START WITCHING HOUR
# --------------------------------------------------

window.mainloop()
