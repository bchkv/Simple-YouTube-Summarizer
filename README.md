# Universal CLI Summarizer

Summarize **YouTube videos**, **PDFs**, **audio/video**, or **text files** using OpenAI.  
Extract text (captions, OCR, or local Whisper), then produce a short plain-language summary on stdout.

Local transcription using Whisper is supported.

## Quick start

```bash
git clone https://github.com/bchkv/Simple-YouTube-Summarizer.git
cd Simple-YouTube-Summarizer

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

pip install -e .
pip install -e ".[faster-transcribe]"   # for --transcribe
pip install -e ".[pdf]"                  # for .pdf files

cp .env.example .env
# set OPENAI_API_KEY in .env

summarize 'https://www.youtube.com/watch?v=VIDEO_ID'
```

Progress logs go to **stderr**; the summary is printed on **stdout**.

## Install

### 1. Base CLI

From the repo root, with a virtualenv active:

```bash
pip install -e .
```

This installs core dependencies (`openai`, `python-dotenv`, `yt-dlp`) and registers the **`summarize`** command.

Verify:

```bash
which summarize
summarize --help
```

You can run `summarize` from any directory while `.venv` is activated.

**Without** editable install, use:

```bash
python main.py SOURCE
```

### 2. Optional extras

| Extra | Command | Used for |
|-------|---------|----------|
| Speech-to-text | `pip install -e ".[faster-transcribe]"` | `--transcribe` (default backend on CPU) |
| Apple Silicon STT | `pip install -e ".[local-transcribe]"` | `--transcribe` with `SUMMARIZER_TRANSCRIPTION_BACKEND=mlx_whisper` |
| PDF | `pip install -e ".[pdf]"` | `.pdf` input |

**System tools:**

| Tool | When |
|------|------|
| [Node.js](https://nodejs.org/) | Recommended for reliable YouTube extraction (`yt-dlp`) |
| [ffmpeg](https://ffmpeg.org/) | YouTube audio download with `--transcribe` |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) + [Poppler](https://poppler.freedesktop.org/) | PDF OCR (scanned pages) |

macOS example:

```bash
brew install node ffmpeg tesseract poppler
```

### 3. API key

```bash
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. The app loads this file from the repo root (and overrides any stale shell export).

## Usage

```bash
summarize SOURCE [-o FILE] [--transcribe] [-m SIZE] [-q]
```

| Flag | Description |
|------|-------------|
| `SOURCE` | YouTube URL, or path to `.pdf`, `.txt`, `.md`, audio, or video |
| `-o FILE` | Write summary to a file instead of stdout |
| `--transcribe` | On-device speech-to-text (see below) |
| `-m`, `--whisper-model` | Whisper size when transcribing (`tiny`, `base`, `small`, `medium`, `large-v3`, `turbo`; aliases `large`, `big`) |
| `-q` | Quiet: print only the summary |

### Examples

```bash
# YouTube — original captions (e.g. en-orig, ru-orig)
summarize 'https://www.youtube.com/watch?v=...'

# YouTube — skip captions; download audio and transcribe locally
summarize 'https://www.youtube.com/watch?v=...' --transcribe -m small

# Local media — always transcribed, then summarized
summarize podcast.mp3 --transcribe

# PDF — embedded text, or OCR if the scan has little text
summarize paper.pdf -o summary.txt

# Plain text
summarize notes.md -q
```

## Input types

### YouTube (default)

- Fetches **original** caption tracks (`*-orig`, e.g. `ru-orig`, `en-orig`) via `yt-dlp`.
- Falls back through other subtitle languages if needed.
- No API cost for extraction; OpenAI is used only for summarization.

### YouTube / media with `--transcribe`

- **YouTube:** ignores captions, downloads audio, runs **faster-whisper** (or MLX if configured).
- **Audio/video files** (`.mp3`, `.wav`, `.mp4`, `.mkv`, …): always transcribed locally, then summarized.
- Transcription progress (per segment or per PDF page) is shown on stderr unless `-q` is set.
- First run downloads Whisper weights (default model: `base`).

### PDF (`.pdf`)

Requires `pip install -e ".[pdf]"` and system **tesseract** + **poppler**.

1. Tries **embedded text** (fast, for digital PDFs).
2. If there is too little text per page, runs **OCR** (Tesseract) page by page.

Force OCR for every page: `SUMMARIZER_PDF_FORCE_OCR=1` in `.env`.

### Text files

Reads UTF-8 text (e.g. `.txt`, `.md`).

## Summarization

Long transcripts are split into chunks, each summarized, then combined with a single **“Summarize:”** prompt.  
Output is plain prose (no fixed report sections).

Models (override in `.env`):

- Chunk pass: `SUMMARIZER_CHUNK_MODEL` (default `gpt-4o-mini`)
- Final pass: `SUMMARIZER_FINAL_MODEL` (default `gpt-5-mini`)

## Configuration (`.env`)

See `.env.example`. Common variables:

```env
OPENAI_API_KEY=sk-...

# On-device transcription (--transcribe)
SUMMARIZER_TRANSCRIPTION_BACKEND=faster_whisper
SUMMARIZER_WHISPER_MODEL=base
SUMMARIZER_WHISPER_DEVICE=cpu
SUMMARIZER_WHISPER_COMPUTE_TYPE=int8

# PDF OCR
# SUMMARIZER_PDF_OCR_DPI=200
# SUMMARIZER_PDF_OCR_LANGUAGE=rus
# SUMMARIZER_PDF_FORCE_OCR=0
```

**Whisper backend:** `faster_whisper` (default when installed) or `mlx_whisper` on Apple Silicon.  
**GPU:** set `SUMMARIZER_WHISPER_DEVICE=cuda` and `SUMMARIZER_WHISPER_COMPUTE_TYPE=float16` (requires CUDA + cuDNN for faster-whisper).

## Requirements

- Python **3.10+**
- OpenAI API key
- **Base:** `pip install -e .`
- **`--transcribe`:** `pip install -e ".[faster-transcribe]"` (or `[local-transcribe]` on MLX)
- **PDF:** `pip install -e ".[pdf]"` plus tesseract and poppler

## Troubleshooting

### `ModuleNotFoundError` after `source .venv/bin/activate`

Your shell may still be using **pyenv shims** instead of the venv. Reinstall inside the project venv:

```bash
deactivate 2>/dev/null || true
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[faster-transcribe]"
pip install -e ".[pdf]"    # if needed
which summarize
python -c "import sys; print(sys.executable)"
```

`sys.executable` should be `.../Summarizer/.venv/bin/python`.

Use `python -m pip install ...`, not bare `pip`, if installs land in the wrong environment.

### YouTube subtitles fail

- Install **Node.js** for `yt-dlp` challenge solving.
- Try without `--transcribe` first (captions are cheaper and often better).
- With `--transcribe`, ensure **ffmpeg** is installed.

### Very short transcript with `--transcribe`

- Check downloaded audio size in stderr logs.
- Try a larger model: `-m small` or `-m medium`.
- For YouTube, compare with caption mode (no `--transcribe`).

### PDF OCR errors

- Install **tesseract** and **poppler** (`brew install tesseract poppler` on macOS).
- Install the Python extra: `pip install -e ".[pdf]"`.
- For Russian scans: `SUMMARIZER_PDF_OCR_LANGUAGE=rus` in `.env`.

### Wrong OpenAI API key

Ensure `.env` in the repo root has the correct key. The app loads it with **override** so it wins over old `export OPENAI_API_KEY=...` in your shell.
