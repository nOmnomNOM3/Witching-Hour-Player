import os
import re
import shutil
import socket
import subprocess
import time
from urllib.parse import unquote, urlparse

VLC_DOWNLOAD_URL = "https://www.videolan.org/vlc/"


def default_candidates():
    files_64 = os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles")
    files_32 = os.environ.get("ProgramFiles(x86)")
    found = []
    if files_64:
        found.append(os.path.join(files_64, "VideoLAN", "VLC", "vlc.exe"))
    if files_32:
        found.append(os.path.join(files_32, "VideoLAN", "VLC", "vlc.exe"))
    found.extend(
        [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
    )
    unique = []
    seen = set()
    for path in found:
        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)
        unique.append(os.path.normpath(path))
    return unique


def find_vlc(preferred=""):
    checked = []
    if preferred:
        checked.append(preferred)
    checked.extend(default_candidates())
    on_path = shutil.which("vlc.exe") or shutil.which("vlc")
    if on_path:
        checked.append(on_path)

    seen = set()
    for path in checked:
        if not path:
            continue
        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)
        if os.path.isfile(path):
            return os.path.normpath(path)
    return ""


def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class VlcSession:
    def __init__(self):
        self.process = None
        self.port = None

    def running(self):
        return self.process is not None and self.process.poll() is None

    def launch(self, vlc_path, items):
        self.port = free_port()
        command = [
            vlc_path,
            "--extraintf=rc",
            "--rc-quiet",
            f"--rc-host=127.0.0.1:{self.port}",
            "--no-one-instance",
        ]
        for item in items:
            path = item.get("path")
            if not path:
                continue
            command.append(path)
            try:
                resume = int(item.get("resume_time", 0))
            except (TypeError, ValueError):
                resume = 0
            if resume > 2:
                command.append(f":start-time={resume}")

        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.process = subprocess.Popen(command, creationflags=flags)
        return self.process

    def rc_text(self, command):
        if not self.port:
            return None
        try:
            sock = socket.create_connection(("127.0.0.1", self.port), timeout=0.5)
            sock.settimeout(0.15)
            try:
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
            except socket.timeout:
                pass
            sock.sendall((command + "\n").encode("utf-8"))
            time.sleep(0.04)
            response = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
            except socket.timeout:
                pass
            sock.close()
            return response.decode("utf-8", errors="ignore")
        except OSError:
            return None

    def rc_number(self, command):
        text = self.rc_text(command)
        if not text:
            return None
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in reversed(lines):
            if re.fullmatch(r"-?\d+", line):
                try:
                    return int(line)
                except ValueError:
                    pass
        numbers = re.findall(r"(?<![\w.])-?\d+(?![\w.])", text)
        if not numbers:
            return None
        try:
            return int(numbers[-1])
        except ValueError:
            return None

    def pause(self):
        return self.rc_text("pause") is not None

    def current_time(self):
        return self.rc_number("get_time")

    def current_length(self):
        return self.rc_number("get_length")

    def current_path(self):
        text = self.rc_text("status")
        if not text:
            return None
        match = re.search(r"new input:\s*(.*?)\s*\)", text, re.IGNORECASE)
        if not match:
            return None
        return normalize_media_path(match.group(1))


def normalize_media_path(path):
    if not path:
        return ""
    path = path.strip().strip("\"'")
    if path.lower().startswith("file://"):
        parsed = urlparse(path)
        path = unquote(parsed.path)
        if re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        path = path.replace("/", os.sep)
    try:
        return os.path.normcase(os.path.abspath(path))
    except OSError:
        return os.path.normcase(path)