from pathlib import Path

from summarizer.config import Settings
from summarizer.transcription.factory import transcribe_local_media


class MediaFileExtractor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def extract(self, source: str) -> str:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        return transcribe_local_media(path, self._settings)
