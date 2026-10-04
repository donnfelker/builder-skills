#!/usr/bin/env python3
"""Send a video to Google Gemini for native video analysis (multimodal mode).

    python3 gemini.py <workdir> --prompt-file PROMPT.md [--model NAME] [--keep-remote]

Needs GEMINI_API_KEY. The skill must ask before running this: it uploads the
video to Google. The key goes in a header, never in the URL. The upload uses
the documented two-step resumable flow, polling stops after --timeout seconds,
and the remote copy is deleted afterwards unless --keep-remote is passed.

Writes gemini.md (the model's answer) and gemini-response.json.
"""

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

API = "https://generativelanguage.googleapis.com"
MIME = {".mp4": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska", ".mov": "video/quicktime",
        ".m4v": "video/mp4", ".avi": "video/x-msvideo", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav"}


RETRY_CODES = (429, 500, 503)
RETRY_WAITS = (10, 20, 40, 60)


def request(method, url, key, data=None, headers=None, timeout=120, retry=False):
    """One API call. With retry=True, waits and retries on 429, 500 and 503 (busy model)."""
    h = {"x-goog-api-key": key}
    h.update(headers or {})
    waits = list(RETRY_WAITS) if retry else []
    while True:
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return resp.headers, (json.loads(body) if body else {})
        except urllib.error.HTTPError as e:
            if e.code in RETRY_CODES and waits:
                wait = waits.pop(0)
                common.warn("Gemini returned HTTP %s; retrying in %d seconds" % (e.code, wait))
                time.sleep(wait)
                continue
            return handle_error(e)
        except urllib.error.URLError as e:
            common.fail("Could not reach Gemini from this environment.", detail=str(e.reason), kind="network",
                        fix="Use visual mode instead, which needs no upload.")


def handle_error(e):
    detail = e.read()[:400].decode("utf-8", "replace")
    if e.code in RETRY_CODES:
        common.fail("Gemini is busy (HTTP %s) and stayed busy after several retries." % e.code, detail=detail,
                    kind="busy", fix="Try again in a few minutes, set a different gemini_model in config, or use visual mode.")
    common.fail("Gemini request failed (HTTP %s)." % e.code, detail=detail,
                fix="Check GEMINI_API_KEY and the model name in config." if e.code in (400, 403, 404) else None)


def upload(path, key):
    size = path.stat().st_size
    mime = MIME.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    start_headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(size),
        "X-Goog-Upload-Header-Content-Type": mime,
        "Content-Type": "application/json",
    }
    body = json.dumps({"file": {"display_name": path.name}}).encode()
    headers, _ = request("POST", API + "/upload/v1beta/files", key, body, start_headers)
    upload_url = headers.get("X-Goog-Upload-URL") or headers.get("x-goog-upload-url")
    if not upload_url:
        common.fail("Gemini did not return an upload URL.")
    with open(path, "rb") as fh:
        _, info = request("POST", upload_url, key, fh, {
            "Content-Length": str(size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        }, timeout=1800)
    return info["file"], mime


def wait_active(name, key, timeout):
    deadline = time.time() + timeout
    while True:
        _, info = request("GET", "%s/v1beta/%s" % (API, name), key)
        state = info.get("state")
        if state == "ACTIVE":
            return info
        if state == "FAILED":
            common.fail("Gemini could not process the video.", detail=json.dumps(info.get("error"))[:300])
        if time.time() > deadline:
            common.fail("Gemini was still processing after %d seconds." % timeout,
                        fix="Run again with a higher --timeout, or use visual mode.")
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep-remote", action="store_true")
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        common.fail("GEMINI_API_KEY is not set.", fix="Use visual mode, or set GEMINI_API_KEY.", kind="no_key")
    cfg = common.load_config()
    model = args.model or cfg["gemini_model"]
    meta = common.load_metadata(args.workdir)
    root = Path(meta["workdir"])
    files = meta.get("files", {})
    video = files.get("video") or files.get("source")
    if not video or not Path(video).exists():
        common.fail("No video file in the workdir.", fix="Run: python3 fetch.py media %s --video" % root)
    prompt = Path(args.prompt_file).read_text()

    remote, mime = upload(Path(video), key)
    remote = wait_active(remote["name"], key, args.timeout)
    payload = {"contents": [{"parts": [
        {"file_data": {"mime_type": mime, "file_uri": remote["uri"]}},
        {"text": prompt},
    ]}]}
    try:
        _, resp = request("POST", "%s/v1beta/models/%s:generateContent" % (API, model), key,
                          json.dumps(payload).encode(), {"Content-Type": "application/json"}, timeout=900, retry=True)
    finally:
        if not args.keep_remote:
            try:
                request("DELETE", "%s/v1beta/%s" % (API, remote["name"]), key)
            except common.Failure:
                common.warn("could not delete the uploaded file; Google removes it after 48 hours")

    common.write_json(root / "gemini-response.json", resp)
    parts = ((resp.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    text = "\n".join(p.get("text", "") for p in parts).strip()
    if not text:
        common.fail("Gemini returned no text.", detail=json.dumps(resp.get("promptFeedback") or resp)[:300])
    (root / "gemini.md").write_text(text + "\n")
    usage = resp.get("usageMetadata") or {}
    common.emit({"status": "ok", "model": model, "output": str(root / "gemini.md"),
                 "input_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount"),
                 "remote_deleted": not args.keep_remote})


if __name__ == "__main__":
    common.run_main(main)
