import sys
from pathlib import Path

from summarizer.config import Settings


def _format_ts(seconds: float) -> str:
    whole = int(seconds)
    mins, secs = divmod(whole, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours:d}:{mins:02d}:{secs:02d}"
    return f"{mins:d}:{secs:02d}"


def transcribe_faster_whisper(
    path: Path, settings: Settings, *, quiet: bool = False
) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "Local transcription with faster-whisper is not installed. "
            "Install with: pip install faster-whisper "
            "or pip install '.[faster-transcribe]'."
        ) from e

    size_mb = path.stat().st_size / (1024 * 1024)
    if not quiet:
        print(
            f"Loading faster-whisper model {settings.whisper_model!r} "
            f"({settings.whisper_device}, {settings.whisper_compute_type})…",
            file=sys.stderr,
        )
        print(f"Audio file: {path.name} ({size_mb:.1f} MB)", file=sys.stderr)

    model = WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )

    transcribe_kwargs: dict = {
        "beam_size": 5,
        # VAD often drops real speech on YouTube rips; keep full audio.
        "vad_filter": False,
    }
    if settings.transcribe_language:
        transcribe_kwargs["language"] = settings.transcribe_language

    if not quiet:
        print("Transcribing…", file=sys.stderr)

    segments, info = model.transcribe(str(path), **transcribe_kwargs)
    if info.language and not quiet:
        prob = getattr(info, "language_probability", None)
        msg = f"Detected speech language: {info.language}"
        if prob is not None:
            msg += f" (p={prob:.2f})"
        print(msg, file=sys.stderr)

    parts: list[str] = []
    last_end = 0.0
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        parts.append(text)
        last_end = max(last_end, float(segment.end))
        if not quiet:
            print(
                f"[{_format_ts(segment.start)} -> {_format_ts(segment.end)}] {text}",
                file=sys.stderr,
            )

    full = " ".join(parts).strip()
    if not full:
        raise RuntimeError("Transcription produced empty text.")

    if not quiet:
        print(
            f"Transcription done: {len(parts)} segments, "
            f"{len(full):,} chars, ~{_format_ts(last_end)} audio",
            file=sys.stderr,
        )
    return full
