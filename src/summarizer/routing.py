import re
from enum import Enum
from pathlib import Path

from summarizer.config import Settings
from summarizer.extractors.base import TextExtractor
from summarizer.extractors.text_file import TextFileExtractor
from summarizer.extractors.youtube import YouTubeExtractor


class SourceKind(Enum):
    YOUTUBE = "youtube"
    TEXT_FILE = "text_file"


_YOUTUBE_HOST_RE = re.compile(
    r"(^|\.)youtube\.com$|(^|\.)youtu\.be$|(^|\.)m\.youtube\.com$",
    re.IGNORECASE,
)


def _is_youtube_url(s: str) -> bool:
    s = s.strip().lower()
    if s.startswith("youtu.be/") or s.startswith("www.youtu.be/"):
        return True
    if not s.startswith(("http://", "https://")):
        return False
    from urllib.parse import urlparse

    try:
        host = urlparse(s).hostname or ""
    except ValueError:
        return False
    return bool(_YOUTUBE_HOST_RE.search(host))


def detect_source_kind(source: str) -> SourceKind:
    raw = source.strip()
    if _is_youtube_url(raw):
        return SourceKind.YOUTUBE
    path = Path(raw).expanduser()
    if path.is_file():
        return SourceKind.TEXT_FILE
    raise ValueError(
        "Expected a YouTube URL or an existing path to a text file."
    )


def extractor_for(kind: SourceKind, settings: Settings) -> TextExtractor:
    if kind is SourceKind.YOUTUBE:
        return YouTubeExtractor(settings)
    if kind is SourceKind.TEXT_FILE:
        return TextFileExtractor()
    raise ValueError(f"Unsupported source kind: {kind!r}")
