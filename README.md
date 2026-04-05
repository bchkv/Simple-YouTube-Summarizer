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

**Local audio/video (Whisper on Apple Silicon):** MLX Whisper is optional so the base install stays portable.

```bash
pip install -e ".[local-transcribe]"
```

You need **`ffmpeg`** on your `PATH` (used to decode media). The first run may download model weights from Hugging Face.

Run (from the repo root, after `pip install -r requirements.txt`):

```bash
python main.py "YouTube URL or path/to/file.txt"
```

Or, if you ran `pip install -e .`:

```bash
summarize "YouTube URL or path/to/file.txt"
```

Use `-o out.txt` to choose the output file (default: `summary.txt`).

**Local transcription flags** (audio/video inputs only):

- `--whisper-model` — e.g. `mlx-community/whisper-small` (default is `whisper-tiny` for speed)
- `--speech-language` — force a language code (e.g. `en`); omit for auto-detect
- `--transcription-backend` — currently `mlx_whisper` (plug-in point for more backends later)

## What it does

- **YouTube:** downloads subtitles with `yt-dlp`, cleans `.vtt` to plain text
- **Audio/video file:** transcribes locally via **MLX Whisper** (see optional extra above), then summarizes
- **Text file:** reads a local UTF-8 file (e.g. `.txt`, `.md`; any extension that is not treated as media)
- splits long text into chunks, summarizes each chunk, then merges into one structured summary

## Requirements

- Python 3.10+
- `yt-dlp`
- an OpenAI API key in a `.env` file
- For local media: **Apple Silicon**, `ffmpeg`, and `pip install -e ".[local-transcribe]"` (or `mlx-whisper` alone)

Example `.env`:

```env
OPENAI_API_KEY=your_api_key_here
