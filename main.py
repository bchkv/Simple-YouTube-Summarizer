#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path

from openai import OpenAI

# -------------------- CONFIG --------------------
YTDLP = "/Users/bochkovoy/.local/bin/yt-dlp"

CHUNK_MODEL = "gpt-4o-mini"
FINAL_MODEL = "gpt-5-mini"

SUB_LANG = "en"
CHUNK_CHARS = 9000  # safe-ish chunk size
VTT_FILE = f"transcript.{SUB_LANG}.vtt"
SUMMARY_FILE = "summary.txt"

client = OpenAI()  # reads OPENAI_API_KEY from environment


# -------------------- VTT -> TEXT --------------------
def vtt_to_text(path: str) -> str:
    s = Path(path).read_text(encoding="utf-8", errors="ignore")

    s = re.sub(r"^\ufeff?WEBVTT.*?\n\n", "", s, flags=re.DOTALL)
    s = re.sub(r"^\d{2}:\d{2}:\d{2}\.\d+\s+-->\s+.*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\d+\s*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\n{2,}", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)

    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


# -------------------- CHUNKING --------------------
def smart_chunk(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    chunks = []
    t = text.strip()
    while len(t) > limit:
        cut = t.rfind("\n", 0, limit)
        if cut == -1:
            cut = t.rfind(". ", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(t[:cut].strip())
        t = t[cut:].strip()
    if t:
        chunks.append(t)
    return chunks


# -------------------- OPENAI SUMMARIZATION --------------------
def summarize_chunk(chunk: str) -> str:
    resp = client.chat.completions.create(
        model=CHUNK_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You summarize technical transcripts faithfully. Do not add info that isn't stated.",
            },
            {
                "role": "user",
                "content": (
                    "Summarize this transcript chunk focusing on technical fidelity:\n"
                    "- Concepts/definitions introduced\n"
                    "- Steps/algorithms/procedures described\n"
                    "- Parameters, numbers, units\n"
                    "- Assumptions, caveats, trade-offs\n"
                    "\nReturn concise bullets.\n\n"
                    f"CHUNK:\n{chunk}"
                ),
            },
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def finalize_summary(part_summaries: list[str]) -> str:
    combined = "\n\n".join(
        f"Part {i+1} summary:\n{summ}" for i, summ in enumerate(part_summaries)
    )

    resp = client.chat.completions.create(
        model=FINAL_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You produce clear, technically accurate synthesis. Avoid speculation.",
            },
            {
                "role": "user",
                "content": (
                    "Combine these part-summaries into a final technical summary with:\n"
                    "1) Overview (3–6 sentences)\n"
                    "2) Technical breakdown (sections with headings)\n"
                    "3) Key parameters / numbers / equations mentioned (if any)\n"
                    "4) Assumptions, limitations, trade-offs\n"
                    "5) Practical takeaways / recommended actions (if any)\n\n"
                    f"{combined}"
                ),
            },
        ],
        temperature=1,
    )
    return resp.choices[0].message.content.strip()


# -------------------- MAIN --------------------
def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: main.py <youtube_url>", file=sys.stderr)
        return 2

    url = sys.argv[1]

    # Ensure we don't accidentally summarize an old file
    Path(VTT_FILE).unlink(missing_ok=True)

    # Download subtitles (always overwrite to transcript.en.vtt)
    cmd = [
        YTDLP,
        "--cookies-from-browser", "firefox",
        "--impersonate", "chrome",
        "--js-runtimes", "node",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", SUB_LANG,
        "--skip-download",
        "--ignore-errors",
        "--paths", ".",
        "-o", "transcript.%(ext)s",
        url,
    ]

    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"yt-dlp returned non-zero exit code: {rc}", file=sys.stderr)

    if not Path(VTT_FILE).exists():
        print(f"Subtitles file not found: {VTT_FILE}", file=sys.stderr)
        return 1

    print(f"Using subtitles: {VTT_FILE}")

    transcript = vtt_to_text(VTT_FILE)
    if not transcript:
        print("Transcript text is empty after cleaning.", file=sys.stderr)
        return 1

    chunks = smart_chunk(transcript, CHUNK_CHARS)
    print(f"Transcript length: {len(transcript):,} chars | chunks: {len(chunks)}")

    part_summaries = []
    for i, ch in enumerate(chunks, 1):
        print(f"Summarizing chunk {i}/{len(chunks)} with {CHUNK_MODEL}...")
        part_summaries.append(summarize_chunk(ch))

    print(f"Creating final summary with {FINAL_MODEL}...")
    summary = finalize_summary(part_summaries)

    Path(SUMMARY_FILE).write_text(summary, encoding="utf-8")
    print(f"Saved summary to: {Path(SUMMARY_FILE).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())