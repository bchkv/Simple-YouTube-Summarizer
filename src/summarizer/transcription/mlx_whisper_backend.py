import sys
from pathlib import Path

from summarizer.config import Settings


def transcribe_mlx(path: Path, settings: Settings, *, quiet: bool = False) -> str:
    try:
        import mlx_whisper
    except ImportError as e:
        raise RuntimeError(
            "Local transcription needs mlx-whisper (MLX on Apple Silicon). "
            "Install with: pip install mlx-whisper "
            "or pip install '.[local-transcribe]'."
        ) from e

    if not quiet:
        print(f"Transcribing with mlx-whisper ({settings.whisper_model})…", file=sys.stderr)

    kwargs: dict = {
        "path_or_hf_repo": settings.whisper_model,
        "verbose": not quiet,
    }
    if settings.transcribe_language:
        kwargs["language"] = settings.transcribe_language

    result = mlx_whisper.transcribe(str(path), **kwargs)
    text = (result.get("text") or "").strip()
    if not text:
        raise RuntimeError("Transcription produced empty text.")
    if not quiet:
        print(f"Transcription done: {len(text):,} chars", file=sys.stderr)
    return text
