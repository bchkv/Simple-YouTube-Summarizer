import re
import sys
import tempfile
from pathlib import Path
from typing import Any

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


def _base_ydl_opts() -> dict[str, Any]:
    return {
        "noplaylist": True,
        "http_headers": _YT_HTTP_HEADERS,
        "js_runtimes": _YT_JS_RUNTIMES,
        "remote_components": _YT_REMOTE_COMPONENTS,
    }


def _extract_video_info(url: str) -> dict[str, Any]:
    opts = {
        **_base_ydl_opts(),
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _collect_subtitle_lang_keys(info: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("subtitles", "automatic_captions"):
        keys.update((info.get(field) or {}).keys())
    return keys


def _pick_original_subtitle_langs(info: dict[str, Any]) -> list[str]:
    """Prefer YouTube *-orig tracks (e.g. en-orig, ru-orig)."""
    keys = _collect_subtitle_lang_keys(info)
    orig = sorted(k for k in keys if k.endswith("-orig"))
    if orig:
        return orig

    manual = sorted((info.get("subtitles") or {}).keys())
    if manual:
        return manual

    audio_lang = (info.get("language") or "").strip()
    if audio_lang:
        return [audio_lang]

    return []


def _subtitle_lang_candidates_explicit(lang: str) -> list[list[str]]:
    raw = lang.strip()
    base = raw.split("-")[0] if raw else ""
    candidates: list[list[str]] = []

    for langs in (
        [raw] if raw else [],
        [f"{base}.*"] if base else [],
        ["all", "-live_chat"],
    ):
        if langs and langs not in candidates:
            candidates.append(langs)
    return candidates


def _subtitle_lang_candidates(
    info: dict[str, Any] | None, lang: str | None
) -> list[list[str]]:
    if lang:
        return _subtitle_lang_candidates_explicit(lang)

    if info is None:
        return [["all", "-live_chat"]]

    candidates: list[list[str]] = []
    keys = _collect_subtitle_lang_keys(info)
    orig = sorted(k for k in keys if k.endswith("-orig"))
    if orig:
        candidates.append(orig)
        base_langs: list[str] = []
        for code in orig:
            base = code[: -len("-orig")]
            if base and base in keys and base not in base_langs:
                base_langs.append(base)
        if base_langs:
            candidates.append(base_langs)

    if not candidates:
        picked = _pick_original_subtitle_langs(info)
        if picked:
            candidates.append(picked)

    fallback = ["all", "-live_chat"]
    if fallback not in candidates:
        candidates.append(fallback)
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


def _find_vtt_file(directory: Path, glob_pattern: str) -> Path | None:
    candidates = sorted(directory.glob(glob_pattern))
    return candidates[0] if candidates else None


def download_subtitles(
    url: str, lang: str | None, transcript_glob: str, dest_dir: Path
) -> Path | None:
    info: dict[str, Any] | None = None
    if not lang:
        try:
            info = _extract_video_info(url)
        except Exception as e:
            print(f"Could not inspect subtitle languages: {e}", file=sys.stderr)

    lang_attempts = _subtitle_lang_candidates(info, lang)
    if info and not lang:
        orig = [k for k in _collect_subtitle_lang_keys(info) if k.endswith("-orig")]
        if orig:
            print(
                f"Using original caption track(s): {', '.join(orig)}",
                file=sys.stderr,
            )
        elif (info.get("subtitles") or {}):
            manual = ", ".join(sorted((info.get("subtitles") or {}).keys()))
            print(f"Using manual caption track(s): {manual}", file=sys.stderr)
        elif info.get("language"):
            print(
                f"No *-orig captions; using audio language: {info['language']}",
                file=sys.stderr,
            )

    for langs in lang_attempts:
        ydl_opts = {
            **_base_ydl_opts(),
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": langs,
            "subtitlesformat": "vtt",
            "outtmpl": str(dest_dir / "transcript.%(ext)s"),
            "quiet": False,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except DownloadError as e:
            print(f"Subtitle download failed for {langs}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(
                f"Unexpected subtitle download error for {langs}: {e}",
                file=sys.stderr,
            )
            continue

        vtt = _find_vtt_file(dest_dir, transcript_glob)
        if vtt:
            return vtt

    return None


def download_youtube_audio(url: str, dest_dir: Path, *, quiet: bool = False) -> Path:
    """Download best-effort audio into dest_dir; return path to the media file."""
    stem = dest_dir / "audio"
    ydl_opts = {
        **_base_ydl_opts(),
        "format": "bestaudio/best",
        "outtmpl": str(stem) + ".%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }
        ],
        "quiet": quiet,
        "no_warnings": quiet,
    }
    if not quiet:
        print("Downloading audio from YouTube…", file=sys.stderr)
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadError as e:
        raise RuntimeError(f"YouTube audio download failed: {e}") from e
    candidates = sorted(dest_dir.glob("audio.*"))
    if not candidates:
        raise RuntimeError("yt-dlp did not produce an audio file.")
    audio = candidates[0]
    if not quiet:
        size_mb = audio.stat().st_size / (1024 * 1024)
        print(f"Downloaded audio: {audio.name} ({size_mb:.1f} MB)", file=sys.stderr)
    return audio


class YouTubeExtractor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract(self, url: str, *, quiet: bool = False) -> str:
        if self._settings.use_transcribe:
            if not quiet:
                print("Transcribing audio on-device (--transcribe)…", file=sys.stderr)
                print(
                    f"Backend: {self._settings.transcription_backend} "
                    f"({self._settings.whisper_model})",
                    file=sys.stderr,
                )
            with tempfile.TemporaryDirectory() as tmp:
                audio_path = download_youtube_audio(url, Path(tmp), quiet=quiet)
                return transcribe_local_media(
                    audio_path.resolve(), self._settings, quiet=quiet
                )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            vtt_path = download_subtitles(
                url,
                self._settings.sub_lang,
                self._settings.transcript_glob,
                tmp_dir,
            )
            if not vtt_path:
                raise RuntimeError(
                    "Could not fetch subtitles. Try again with --transcribe to use "
                    "on-device speech-to-text, or check that the video has captions."
                )
            transcript = vtt_to_text(str(vtt_path))
            if not transcript:
                raise RuntimeError("Transcript text is empty after cleaning.")
            if not quiet:
                print("Using downloaded subtitles.", file=sys.stderr)
            return transcript
