from typing import Protocol


class TextExtractor(Protocol):
    def extract(self, source: str) -> str: ...
