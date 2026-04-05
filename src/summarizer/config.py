from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    chunk_model: str = "gpt-4o-mini"
    final_model: str = "gpt-5-mini"
    sub_lang: str = "en"
    chunk_chars: int = 9000
    summary_file: str = "summary.txt"
    transcript_glob: str = "transcript*.vtt"


DEFAULT_SETTINGS = Settings()
