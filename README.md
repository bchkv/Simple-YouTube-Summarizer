## Purpose

Get YouTube video summaries for **under a cent per video.**

## Usage

Install dependencies:

`pip install -r requirements.txt`

Edit `.env` adding your OpenAI's API key

Run

```bash
./yt-summarize "YouTube URL"
```

## What it does

- downloads subtitles from a YouTube video with `yt-dlp`
- cleans and extracts transcript text from `.vtt`
- splits long transcripts into chunks
- summarizes each chunk
- produces one final structured summary

## Requirements

- Python 3.10+
- `yt-dlp`
- an OpenAI API key in a `.env` file

Example `.env`:

```env
OPENAI_API_KEY=your_api_key_here
