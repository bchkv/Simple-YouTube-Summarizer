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
    # Local speech-to-text (see summarizer.transcription.factory)
    transcription_backend: str = "mlx_whisper"
    whisper_model: str = "mlx-community/whisper-tiny"
    transcribe_language: str | None = None
    # YouTube: False = captions via yt-dlp; True = download audio + local STT
    youtube_local_transcribe: bool = False


DEFAULT_SETTINGS = Settings()
