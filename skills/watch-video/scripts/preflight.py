#!/usr/bin/env python3
"""Report what this environment can do, as JSON.

    python3 preflight.py                 # report only
    python3 preflight.py --install       # also install missing pieces
    python3 preflight.py --no-network    # skip the reachability probes

On macOS, installs use Homebrew (yt-dlp, ffmpeg) and uv or pip (mlx-whisper).
Everywhere else, installs go into a private venv under ~/.cache/watch-video.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

HOSTS = {
    "youtube": "https://www.youtube.com/robots.txt",
    "huggingface": "https://huggingface.co/api/models?limit=1",
    "pypi": "https://pypi.org/simple/yt-dlp/",
    "gemini": "https://generativelanguage.googleapis.com/",
    "openai": "https://api.openai.com/v1/models",
}

KEYS = ["GEMINI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"]

NETWORK_FIX = common.NETWORK_RISK


def run(cmd, timeout=600):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def tool_version(path, flag="--version"):
    if not path:
        return None
    code, out = run([path, flag], timeout=30)
    return out.splitlines()[0][:80] if code == 0 and out else None


def reachable(url):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "watch-video-preflight"})
    try:
        with urllib.request.urlopen(req, timeout=8):
            return True
    except urllib.error.HTTPError:
        return True  # the host answered, even if with 401/403/404
    except Exception:
        return False


def gpu():
    if shutil.which("nvidia-smi"):
        code, _ = run(["nvidia-smi", "-L"], timeout=15)
        if code == 0:
            return "cuda"
    if common.is_apple_silicon():
        return "apple"
    return None


def whisper_backends():
    found = {}
    if common.is_apple_silicon():
        py = common.python_with_module("mlx_whisper")
        if py:
            found["mlx_whisper"] = {"python": py}
        elif shutil.which("mlx_whisper"):
            found["mlx_whisper"] = {"cli": shutil.which("mlx_whisper")}
    py = common.python_with_module("faster_whisper")
    if py:
        found["faster_whisper"] = {"python": py}
    return found


def writable(path):
    """Test the folder, or its nearest existing parent, without creating it."""
    while not path.exists() and path != path.parent:
        path = path.parent
    try:
        with tempfile.NamedTemporaryFile(dir=str(path)):
            pass
        return True
    except OSError:
        return False


def ensure_venv(report):
    if common.venv_python():
        return str(common.venv_python())
    if sys.version_info < (3, 10):
        report["install_log"].append("Python %s is too old for yt-dlp (needs 3.10+)." % platform.python_version())
        return None
    common.cache_dir().mkdir(parents=True, exist_ok=True)
    code, out = run([sys.executable, "-m", "venv", str(common.venv_dir())])
    report["install_log"].append("venv: %s" % ("ok" if code == 0 else out[-300:]))
    return str(common.venv_python()) if code == 0 else None


def pip_install(report, packages):
    py = ensure_venv(report)
    if not py:
        return False
    code, out = run([py, "-m", "pip", "install", "--upgrade", "--quiet"] + packages, timeout=1800)
    report["install_log"].append("pip install %s: %s" % (" ".join(packages), "ok" if code == 0 else out[-400:]))
    return code == 0


def install_missing(report):
    tools = report["tools"]
    if common.is_mac():
        brew = shutil.which("brew")
        for name in ("yt-dlp", "ffmpeg"):
            if not tools[name]["path"]:
                if brew:
                    code, out = run([brew, "install", name], timeout=1800)
                    report["install_log"].append("brew install %s: %s" % (name, "ok" if code == 0 else out[-300:]))
                else:
                    report["install_log"].append("Homebrew not found. Install it from https://brew.sh, then: brew install %s" % name)
        if common.is_apple_silicon() and "mlx_whisper" not in report["whisper"]["backends"]:
            uv = shutil.which("uv")
            if uv:
                code, out = run([uv, "tool", "install", "mlx-whisper"], timeout=1800)
                report["install_log"].append("uv tool install mlx-whisper: %s" % ("ok" if code == 0 else out[-300:]))
            else:
                pip_install(report, ["mlx-whisper"])
    else:
        packages = []
        if not tools["yt-dlp"]["path"]:
            packages.append("yt-dlp")
        if not tools["ffmpeg"]["path"]:
            packages.append("imageio-ffmpeg")
        if not report["whisper"]["backends"]:
            packages.append("faster-whisper")
        if packages:
            pip_install(report, packages)


def build_report(probe_network):
    cfg = common.load_config()
    ytdlp = common.find_tool("yt-dlp")
    ffmpeg = common.find_ffmpeg()
    ffprobe = common.find_tool("ffprobe")
    node = shutil.which("node")
    deno = shutil.which("deno")
    out_dir = common.output_base(cfg)
    report = {
        "os": sys.platform,
        "machine": platform.machine(),
        "apple_silicon": common.is_apple_silicon(),
        "python": {
            "version": platform.python_version(),
            "path": sys.executable,
            "scripts_ok": sys.version_info >= (3, 9),
            "pip_ytdlp_ok": sys.version_info >= (3, 10),
        },
        "venv": str(common.venv_python()) if common.venv_python() else None,
        "tools": {
            "yt-dlp": {"path": ytdlp, "version": tool_version(ytdlp)},
            "ffmpeg": {"path": ffmpeg, "version": tool_version(ffmpeg, "-version")},
            "ffprobe": {"path": ffprobe},
            "node": {"path": node, "version": tool_version(node)},
            "deno": {"path": deno},
        },
        "youtube_js_runtime": bool(node or deno),
        "whisper": {"backends": whisper_backends(), "gpu": gpu()},
        "keys": {k: bool(os.environ.get(k)) for k in KEYS},
        "output_dir": {"path": str(out_dir), "writable": writable(out_dir)},
        "claude_sandbox": common.in_claude_sandbox(),
        "network": {},
        "install_log": [],
    }
    if probe_network:
        report["network"] = {name: reachable(url) for name, url in HOSTS.items()}
    return report


def summarize(report):
    """Plain-language list of what works and what does not."""
    can, cannot = [], []
    t = report["tools"]
    net = report["network"]
    if not net.get("youtube", True):
        cannot.append("download from URLs: the network here blocks video sites. " + NETWORK_FIX +
                      " Or attach the video file instead, which needs no network change.")
    elif t["yt-dlp"]["path"]:
        can.append("download from video URLs")
    else:
        cannot.append("download from URLs (yt-dlp missing: %s)" % common.install_hint("yt-dlp"))
    if t["ffmpeg"]["path"]:
        can.append("extract audio and frames")
    else:
        cannot.append("extract audio or frames (ffmpeg missing: %s)" % common.install_hint("ffmpeg"))
    if report["whisper"]["backends"] and net.get("huggingface", True):
        can.append("transcribe locally with " + ", ".join(report["whisper"]["backends"]))
    elif not net.get("huggingface", True):
        cannot.append("transcribe locally: the network here blocks the Whisper model download (huggingface.co). " +
                      NETWORK_FIX + " Or provide a transcript file (.vtt, .srt, .txt) with the video.")
    else:
        cannot.append("transcribe locally (no Whisper: %s)" % common.install_hint("whisper"))
    if report["keys"]["GEMINI_API_KEY"]:
        can.append("multimodal mode (Gemini key set)")
    if report["keys"]["OPENAI_API_KEY"] or report["keys"]["GROQ_API_KEY"]:
        can.append("hosted transcription (asks before upload)")
    if not report["output_dir"]["writable"]:
        cannot.append("write to %s" % report["output_dir"]["path"])
    if t["yt-dlp"]["path"] and not report["youtube_js_runtime"]:
        cannot.append("read some YouTube videos reliably (no Node or Deno for yt-dlp)")
    report["can"] = can
    report["cannot"] = cannot
    report["status"] = "ok" if not cannot else "limited"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--install", action="store_true", help="install missing dependencies")
    ap.add_argument("--no-network", action="store_true", help="skip reachability probes")
    args = ap.parse_args()

    if sys.version_info < (3, 9):
        common.fail("Python %s is too old. watch-video needs Python 3.9 or newer." % platform.python_version())

    report = build_report(not args.no_network)
    if args.install:
        install_missing(report)
        log = report["install_log"]
        report = build_report(not args.no_network)
        report["install_log"] = log
    summarize(report)
    common.emit(report)


if __name__ == "__main__":
    common.run_main(main)
