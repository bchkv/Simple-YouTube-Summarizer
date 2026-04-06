import re
import sys
import tempfile
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from summarizer.config import Settings
from summarizer.transcription.factory import transcribe_local_media


_YT_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}
_YT_JS_RUNTIMES = {"node": {}, "deno": {}}
_YT_REMOTE_COMPONENTS = ["ejs:github"]


def _subtitle_lang_candidates(lang: str) -> list[list[str]]:
    raw = (lang or "").strip()
    base = raw.split("-")[0] if raw else ""
    candidates: list[list[str]] = []

    for langs in (
        [raw] if raw else [],
        [f"{base}.*"] if base else [],
        ["en", "en.*"] if base != "en" else [],
        ["all", "-live_chat"],
    ):
        if langs and langs not in candidates:
            candidates.append(langs)
    return candidates


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

    for langs in _subtitle_lang_candidates(lang):
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": langs,
            "subtitlesformat": "vtt",
            "outtmpl": "transcript.%(ext)s",
            "noplaylist": True,
            "quiet": False,
            "http_headers": _YT_HTTP_HEADERS,
            "js_runtimes": _YT_JS_RUNTIMES,
            "remote_components": _YT_REMOTE_COMPONENTS,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except DownloadError as e:
            print(f"Subtitle download failed for {langs}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"Unexpected subtitle download error for {langs}: {e}", file=sys.stderr)
            continue

        vtt = _find_vtt_file(transcript_glob)
        if vtt:
            return vtt

    return None


def download_youtube_audio(url: str, dest_dir: Path) -> Path:
    """Download best-effort audio into dest_dir; return path to the media file."""
    stem = dest_dir / "audio"
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(stem) + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "http_headers": _YT_HTTP_HEADERS,
        "js_runtimes": _YT_JS_RUNTIMES,
        "remote_components": _YT_REMOTE_COMPONENTS,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadError as e:
        raise RuntimeError(f"YouTube audio download failed: {e}") from e
    candidates = sorted(dest_dir.glob("audio.*"))
    if not candidates:
        raise RuntimeError("yt-dlp did not produce an audio file.")
    return candidates[0]


class YouTubeExtractor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract(self, url: str) -> str:
        if self._settings.youtube_local_transcribe:
            with tempfile.TemporaryDirectory() as tmp:
                audio_path = download_youtube_audio(url, Path(tmp))
                return transcribe_local_media(audio_path.resolve(), self._settings)

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
