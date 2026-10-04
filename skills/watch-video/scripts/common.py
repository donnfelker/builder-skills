"""Shared helpers for the watch-video scripts.

Standard library only, Python 3.9+. Every script prints one JSON object on
stdout so the skill can read the result without parsing prose.
"""

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG = {
    "output_dir": None,
    "language": None,
    "whisper_model_mlx": "mlx-community/whisper-large-v3-turbo",
    "whisper_model_gpu": "large-v3-turbo",
    "whisper_model_cpu": "small",
    "chunk_seconds": 600,
    "max_frames": 120,
    "confirm_frames_over": 60,
    "gemini_model": "gemini-3.8-flash",
    "hosted_provider": "openai",
}


def is_mac():
    return sys.platform == "darwin"


def is_apple_silicon():
    return is_mac() and platform.machine() == "arm64"


# ---------- config and paths ----------

def config_paths():
    paths = []
    if os.environ.get("WATCH_VIDEO_CONFIG"):
        paths.append(Path(os.environ["WATCH_VIDEO_CONFIG"]).expanduser())
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    paths.append(Path(xdg) / "watch-video" / "config.json")
    paths.append(SKILL_DIR / "config.json")
    return paths


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    for p in config_paths():
        if p.is_file():
            try:
                cfg.update({k: v for k, v in json.loads(p.read_text()).items() if v is not None})
            except (OSError, ValueError) as e:
                warn("could not read config %s: %s" % (p, e))
            break
    return cfg


def output_base(cfg=None):
    cfg = cfg or load_config()
    raw = os.environ.get("WATCH_VIDEO_DIR") or cfg.get("output_dir") or "./videos"
    return Path(raw).expanduser().resolve()


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "watch-video"


def venv_dir():
    return cache_dir() / "venv"


def venv_python():
    p = venv_dir() / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return p if p.exists() else None


# ---------- tool discovery ----------

def find_tool(name):
    """PATH first, then the skill's private venv."""
    found = shutil.which(name)
    if found:
        return found
    candidate = venv_dir() / "bin" / name
    if candidate.exists():
        return str(candidate)
    return None


def python_has_module(python, module):
    try:
        r = subprocess.run([python, "-c", "import %s" % module],
                           capture_output=True, timeout=60)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def python_with_module(module):
    """Return a Python interpreter that can import `module`, or None."""
    candidates = [sys.executable]
    vp = venv_python()
    if vp:
        candidates.append(str(vp))
    for py in candidates:
        if python_has_module(py, module):
            return py
    return None


def find_ffmpeg():
    found = find_tool("ffmpeg")
    if found:
        return found
    py = python_with_module("imageio_ffmpeg")
    if py:
        r = subprocess.run([py, "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return None


def require_ffmpeg():
    ff = find_ffmpeg()
    if not ff:
        fail("ffmpeg is not installed.", fix=install_hint("ffmpeg"))
    return ff


def install_hint(tool):
    mac = {
        "yt-dlp": "brew install yt-dlp",
        "ffmpeg": "brew install ffmpeg",
        "whisper": "uv tool install mlx-whisper   (or: pip install mlx-whisper)",
    }
    other = {
        "yt-dlp": "python3 scripts/preflight.py --install",
        "ffmpeg": "install ffmpeg with your package manager, or: python3 scripts/preflight.py --install",
        "whisper": "python3 scripts/preflight.py --install",
    }
    return (mac if is_mac() else other).get(tool, "")


def media_duration(path):
    """Seconds, using ffprobe when present, else parsing `ffmpeg -i`."""
    probe = find_tool("ffprobe")
    if probe:
        r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                           capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    ff = find_ffmpeg()
    if not ff:
        return None
    r = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return None


# ---------- time helpers ----------

def parse_time(value):
    """'1:02:03', '10:00', '90', '90.5' -> seconds (float). None passes through."""
    if value is None or value == "":
        return None
    parts = str(value).strip().split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        raise ValueError("bad time: %r (use 10:00, 1:02:03 or seconds)" % value)
    total = 0.0
    for n in nums:
        total = total * 60 + n
    return total


def fmt_ts(seconds):
    seconds = max(0, int(seconds or 0))
    return "%02d:%02d:%02d" % (seconds // 3600, (seconds % 3600) // 60, seconds % 60)


def slugify(text, max_len=50):
    text = re.sub(r"[^\w\s-]", "", (text or "").lower(), flags=re.UNICODE)
    words = re.sub(r"[\s_]+", " ", text).strip().split(" ")[:6]
    slug = "-".join(w for w in words if w)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return (slug[:max_len].strip("-")) or "video"


def short_hash(text, n=8):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


# ---------- workdir state ----------

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def write_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def load_metadata(workdir):
    meta = read_json(Path(workdir) / "metadata.json")
    if not meta:
        fail("No metadata.json in %s. Run fetch.py meta first." % workdir)
    return meta


def save_metadata(workdir, meta):
    write_json(Path(workdir) / "metadata.json", meta)


# ---------- output ----------

def warn(msg):
    print("warning: " + msg, file=sys.stderr)


def emit(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


class Failure(Exception):
    """A step failed. `payload` is the JSON the script prints."""

    def __init__(self, payload):
        super().__init__(payload.get("error"))
        self.payload = payload


def fail(message, fix=None, **extra):
    out = {"status": "error", "error": message}
    if fix:
        out["fix"] = fix
    out.update(extra)
    raise Failure(out)


def run_main(fn):
    """Run a script's main, printing a Failure as JSON with exit code 1."""
    try:
        fn()
    except Failure as f:
        emit(f.payload)
        sys.exit(1)
