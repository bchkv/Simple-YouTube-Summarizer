from pathlib import Path

from summarizer.config import Settings


def transcribe_mlx(path: Path, settings: Settings) -> str:
    try:
        import mlx_whisper
    except ImportError as e:
        raise RuntimeError(
            "Local transcription needs mlx-whisper (MLX on Apple Silicon). "
            "Install with: pip install mlx-whisper "
            "or pip install '.[local-transcribe]'."
        ) from e

    kwargs: dict = {"path_or_hf_repo": settings.whisper_model}
    if settings.transcribe_language:
        kwargs["language"] = settings.transcribe_language

    result = mlx_whisper.transcribe(str(path), verbose=False, **kwargs)
    text = (result.get("text") or "").strip()
    if not text:
        raise RuntimeError("Transcription produced empty text.")
    return text
