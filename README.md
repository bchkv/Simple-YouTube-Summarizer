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

Run (from the repo root, after `pip install -r requirements.txt`):

```bash
python main.py "YouTube URL or path/to/file.txt"
```

Or, if you ran `pip install -e .`:

```bash
summarize "YouTube URL or path/to/file.txt"
```

Use `-o out.txt` to choose the output file (default: `summary.txt`).

## What it does

- **YouTube:** downloads subtitles with `yt-dlp`, cleans `.vtt` to plain text
- **Text file:** reads a local UTF-8 file (e.g. `.txt`, `.md`)
- splits long text into chunks, summarizes each chunk, then merges into one structured summary

## Requirements

- Python 3.10+
- `yt-dlp`
- an OpenAI API key in a `.env` file

Example `.env`:

```env
OPENAI_API_KEY=your_api_key_here
