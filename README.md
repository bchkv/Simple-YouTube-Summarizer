# Universal CLI Summarizer

Summarize YouTube videos, PDFs, audio/video, or text with OpenAI.  
Summary on **stdout**; progress on **stderr**.

## Install `summarize` (system-wide)

You need **Python 3.10+**. On macOS, install it if needed (`brew install python`).

### Option A — recommended: [pipx](https://pipx.pypa.io/)

Installs the `summarize` command into `~/.local/bin` (isolated from other projects).

```bash
brew install pipx
pipx ensurepath
# restart the terminal or: source ~/.zshrc

git clone https://github.com/bchkv/Universal-CLI-Summarizer.git
cd Universal-CLI-Summarizer

pipx install .
# PDF support is optional:
# pipx install --force '.[pdf]'
```

Check:

```bash
which summarize   # should be ~/.local/bin/summarize
summarize --help
```

### Option B — project venv on your `PATH`

```bash
git clone https://github.com/bchkv/Universal-CLI-Summarizer.git
cd Universal-CLI-Summarizer

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -e ".[pdf]"                  # optional: PDF files
```

Add the venv to your shell (once), then open a new terminal:

```bash
echo 'export PATH="$HOME/Universal-CLI-Summarizer/.venv/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Adjust the path if you cloned somewhere else. Verify with `which summarize`.

### System tools (optional)

```bash
brew install node ffmpeg          # YouTube; ffmpeg for --transcribe
brew install tesseract poppler    # PDF OCR (with pip extra [pdf])
```

## API key

```bash
summarize config set-key
```

Prompts securely and saves to `~/.config/summarizer/.env`.

```bash
summarize config show
summarize config path
summarize config unset-key
```

For hacking on the repo, you can use a project `.env` instead (`cp .env.example .env`). See `.env.example` for advanced `SUMMARIZER_*` settings.

## Usage

```bash
summarize SOURCE [-o FILE] [--transcribe] [-m SIZE] [--transcript] [-q]
```

| Flag | Meaning |
|------|---------|
| `-o FILE` | Write output to a file |
| `--transcribe` | Local Whisper (YouTube: skip captions) |
| `-m SIZE` | Whisper model: `tiny`, `base`, `small`, `medium`, `large-v3`, `turbo` |
| `--transcript` | Output the full extracted transcript and skip summarization |
| `-q` | Only print the final output |

```bash
summarize 'https://www.youtube.com/watch?v=...'
summarize 'https://www.youtube.com/watch?v=...' --transcribe -m small
summarize podcast.mp3 --transcribe
summarize 'https://www.youtube.com/watch?v=...' --transcript -o transcript.txt
summarize paper.pdf -o summary.txt
summarize notes.md -q
```

**Sources:** YouTube captions (`*-orig` by default), local media (with `--transcribe`), PDF (text + OCR), `.txt` / `.md`.  
Temporary YouTube subtitle files are kept in a temp directory and are not written to your current folder unless you use `-o`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: summarize` | Use pipx (`pipx ensurepath`) or add `.venv/bin` to `PATH` |
| `ModuleNotFoundError` | Wrong Python: use the venv or reinstall with `pipx install .` |
| Missing / bad API key | `summarize config set-key` or `unset OPENAI_API_KEY` if an old export conflicts |
| YouTube fails | `brew install node`; try without `--transcribe` first |
| PDF OCR fails | `pip install -e ".[pdf]"` and `brew install tesseract poppler` |
