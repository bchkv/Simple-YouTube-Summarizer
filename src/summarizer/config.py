from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    # Keep CLI usable even if optional dotenv isn't installed.
    def load_dotenv() -> bool:
        return False

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=_REPO_ROOT / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    chunk_model: str = "gpt-4o-mini"
    final_model: str = "gpt-5-mini"
    sub_lang: str = "en"
    chunk_chars: int = 9000
    transcript_glob: str = "transcript*.vtt"
    # Local speech-to-text (see summarizer.transcription.factory)
    transcription_backend: str = "mlx_whisper"
    whisper_model: str = "mlx-community/whisper-tiny"
    transcribe_language: str | None = None
    # YouTube: False = captions via yt-dlp; True = download audio + local STT
    youtube_local_transcribe: bool = False


DEFAULT_SETTINGS = Settings()
