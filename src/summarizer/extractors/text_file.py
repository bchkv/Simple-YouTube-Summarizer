from pathlib import Path


class TextFileExtractor:
    def extract(self, source: str) -> str:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        return text.strip()
