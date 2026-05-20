## Purpose

Get YouTube video summaries for **under a cent per video.**

## Usage

Install dependencies:

`pip install -r requirements.txt`

Edit `.env` adding your OpenAI's API key

Install the package (optional; adds the `summarize` command):

```bash
pip install -e .
```

**On-device transcription** (`--transcribe`) uses **faster-whisper** by default when installed:

```bash
pip install -e ".[faster-transcribe]"
```

Optional Apple Silicon backend:

```bash
pip install -e ".[local-transcribe]"
# then set SUMMARIZER_TRANSCRIPTION_BACKEND=mlx_whisper in .env
```

The first `--transcribe` run downloads Whisper weights (e.g. `base`). PyAV bundles FFmpeg; no system `ffmpeg` required for faster-whisper.

Run (from the repo root, after `pip install -r requirements.txt`):

```bash
python main.py "YouTube URL or path/to/file.txt"
```

Or, if you ran `pip install -e .`:

```bash
summarize "YouTube URL or path/to/file.txt"
```

The final summary goes to **stdout** (progress logs go to stderr).

```bash
summarize SOURCE [-o FILE] [--transcribe] [-q]
```

| Flag | Purpose |
|------|---------|
| `SOURCE` | YouTube URL or path to a text / audio / video file |
| `-o FILE` | Write summary to a file instead of stdout |
| `--transcribe` | Use on-device STT (YouTube: skip captions; media: always) |
| `-q` | Quiet: print only the summary |

Examples:

```bash
summarize 'https://www.youtube.com/watch?v=...'
summarize 'https://www.youtube.com/watch?v=...' --transcribe
summarize podcast.mp3 -o notes.txt
summarize lecture.txt -q
```

Advanced transcription/model settings live in `.env` (see `.env.example`), not on the CLI.

## What it does

- **YouTube:** downloads **original** captions (`*-orig`) by default; `--transcribe` skips captions and uses on-device STT instead
- **Audio/video file:** transcribes locally via **MLX Whisper** or **faster-whisper**, then summarizes
- **Text file:** reads a local UTF-8 file (e.g. `.txt`, `.md`; any extension that is not treated as media)
- splits long text into chunks, summarizes each chunk, then merges into one structured summary

## Requirements

- Python 3.10+
- `yt-dlp`
- an OpenAI API key in a `.env` file
- For `--transcribe`: `pip install -e ".[faster-transcribe]"` (CPU; CUDA if configured in `.env`)

Example `.env`:

```env
OPENAI_API_KEY=your_api_key_here
```

## Troubleshooting: wrong Python environment

If you see `ModuleNotFoundError` for packages from `requirements.txt` (for example `openai` or `dotenv`) even after activating `venv`, your shell may be using `pyenv` shims instead of this repo's virtualenv.

Recreate the venv and reinstall in this project:

```bash
deactivate 2>/dev/null || true
rm -rf venv
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import sys; print(sys.executable)"
```

The printed executable should be:
`/Users/bochkovoy/Projects/Summarizer/venv/bin/python`