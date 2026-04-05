#!/usr/bin/env python3
"""
yt_to_transcript.py
Reads a YouTube URL from stdin → downloads the audio → transcribes it
with whisper-mlx (large-v3-turbo) → prints the transcript to stdout.

Tested on Apple-Silicon (M-series) with Python 3.11 + mlx-whisper.
"""

import os
import sys
import time
import tempfile
import threading
import itertools
import yt_dlp
import re
import logging
try:
    import pyperclip
    HAS_CLIP = True
except ImportError:
    HAS_CLIP = False

# --- MLX Whisper ------------------------------------------------------
import mlx_whisper   # pip install whisper-mlx
# ---------------------------------------------------------------------
# 0.  Environment & tiny spinner util
# ---------------------------------------------------------------------
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"   # harmless if MKL is pulled in anywhere

def start_spinner(msg: str):
    """Print an ASCII spinner until the returned stop() is called."""
    stop_event = threading.Event()

    def _spin():
        for ch in itertools.cycle("|/-\\"):
            if stop_event.is_set():
                break
            print(f"\r{msg} {ch}", end="", file=sys.stderr)
            time.sleep(0.1)
        print("\r" + " " * (len(msg) + 2) + "\r", end="", file=sys.stderr)

    threading.Thread(target=_spin, daemon=True).start()
    return stop_event.set

# ---------------------------------------------------------------------
# 1.  Read YouTube URL from Shortcuts / stdin
# ---------------------------------------------------------------------
YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/"
)

url = sys.stdin.read().strip()
if not url or not YOUTUBE_REGEX.match(url):
    sys.exit(f"Invalid or missing YouTube URL received on stdin!")

print(f"URL received: {url}", file=sys.stderr)

# ---------------------------------------------------------------------
# 2.  Download best-quality audio to a temp file
# ---------------------------------------------------------------------
with tempfile.TemporaryDirectory() as temp_dir:
    audio_path = os.path.join(temp_dir, "audio")   # yt-dl will append .m4a


    class StderrLogger(object):
        def debug(self, msg):
            print(msg, file=sys.stderr)

        def warning(self, msg):
            print(msg, file=sys.stderr)

        def error(self, msg):
            print(msg, file=sys.stderr)


    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": audio_path,
        "quiet": True,  # Quiet reduces non-error output
        "no_warnings": True,  # Suppress warnings
        "logger": StderrLogger(),  # Force all yt-dlp logs to stderr
        "progress_hooks": [],  # Remove if you have any progress hooks
        "noplaylist": True,
    }
    yt_dlp.YoutubeDL(ydl_opts).download([url])

    # -----------------------------------------------------------------
    # 3.  Transcribe with whisper-mlx (large-v3-turbo)
    # -----------------------------------------------------------------
    print("Loading whisper-mlx model…", file=sys.stderr)
    # First run will download the MLX‐converted weights (~1.6 GB)

    # Spinner while transcribing
    stop_spin = start_spinner("Transcribing…")

    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo="mlx-community/whisper-small-mlx",
        # word_timestamps=True,         # enable if you need word-level times
    )

    stop_spin()        # stop spinner
    print("Transcribing… done", file=sys.stderr)

    transcript = result["text"]

# ---------------------------------------------------------------------
# 4.  Output transcript (captured by Shortcuts)
# ---------------------------------------------------------------------
print(transcript)
