import re
import sys
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from summarizer.config import Settings


def vtt_to_text(path: str) -> str:
    s = Path(path).read_text(encoding="utf-8", errors="ignore")

    s = re.sub(r"^\ufeff?WEBVTT.*?\n\n", "", s, flags=re.DOTALL)
    s = re.sub(
        r"^\d{2}:\d{2}:\d{2}\.\d+\s+-->\s+.*$",
        "",
        s,
        flags=re.MULTILINE,
    )
    s = re.sub(r"^\d+\s*$", "", s, flags=re.MULTILINE)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\n{2,}", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)

    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def _cleanup_transcripts(glob_pattern: str) -> None:
    for p in Path(".").glob(glob_pattern):
        p.unlink(missing_ok=True)


def _find_vtt_file(glob_pattern: str) -> Path | None:
    candidates = sorted(Path(".").glob(glob_pattern))
    return candidates[0] if candidates else None


def download_subtitles(url: str, lang: str, transcript_glob: str) -> Path | None:
    _cleanup_transcripts(transcript_glob)

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [lang],
        "subtitlesformat": "vtt",
        "outtmpl": "transcript.%(ext)s",
        "noplaylist": True,
        "quiet": False,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        },
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadError as e:
        print(f"Subtitle download failed: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected subtitle download error: {e}", file=sys.stderr)
        return None

    return _find_vtt_file(transcript_glob)


class YouTubeExtractor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract(self, url: str) -> str:
        vtt_path = download_subtitles(
            url,
            self._settings.sub_lang,
            self._settings.transcript_glob,
        )
        if not vtt_path:
            raise RuntimeError(
                "Could not fetch subtitles. The video may have no subtitles, "
                "or YouTube may be rate-limiting the request."
            )
        transcript = vtt_to_text(str(vtt_path))
        if not transcript:
            raise RuntimeError("Transcript text is empty after cleaning.")
        return transcript
