from pathlib import Path

from summarizer.config import Settings


def transcribe_local_media(path: Path, settings: Settings) -> str:
    key = settings.transcription_backend.lower().replace("-", "_")
    if key in ("mlx_whisper", "mlx"):
        from summarizer.transcription.mlx_whisper_backend import transcribe_mlx

        return transcribe_mlx(path, settings)
    raise ValueError(
        f"Unknown transcription backend {settings.transcription_backend!r}. "
        "Supported values: mlx_whisper, mlx."
    )
