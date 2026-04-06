import argparse
import sys
from dataclasses import replace
from pathlib import Path

from summarizer.config import Settings
from summarizer.pipeline import finalize_summary, smart_chunk, summarize_chunk
from summarizer.routing import SourceKind, detect_source_kind, extractor_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize YouTube (captions by default; optional on-device STT), "
            "local audio/video (Whisper), or plain text files."
        ),
    )
    parser.add_argument(
        "source",
        help="YouTube URL or path to a text, audio, or video file",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=None,
        help=(
            "Write summary to this file instead of stdout "
            "(use - for stdout explicitly)."
        ),
    )
    parser.add_argument(
        "--transcription-backend",
        metavar="NAME",
        default=None,
        help=(
            "Local STT backend (default: mlx_whisper). "
            "Use mlx_whisper for Apple Silicon / MLX."
        ),
    )
    parser.add_argument(
        "--whisper-model",
        metavar="ID",
        default=None,
        help=(
            "Whisper weights: Hugging Face repo or local path "
            f"(default: {Settings().whisper_model})"
        ),
    )
    parser.add_argument(
        "--speech-language",
        metavar="CODE",
        default=None,
        help=(
            "Language code for local transcription (e.g. en). "
            "Omitted = auto-detect on multilingual models."
        ),
    )
    parser.add_argument(
        "--youtube-local-transcribe",
        action="store_true",
        help=(
            "For YouTube URLs: download audio and transcribe on-device "
            "(default: use YouTube captions / auto-generated subs)."
        ),
    )
    args = parser.parse_args(argv)

    settings = Settings()
    overrides: dict = {}
    if args.transcription_backend is not None:
        overrides["transcription_backend"] = args.transcription_backend
    if args.whisper_model is not None:
        overrides["whisper_model"] = args.whisper_model
    if args.speech_language is not None:
        overrides["transcribe_language"] = args.speech_language
    if args.youtube_local_transcribe:
        overrides["youtube_local_transcribe"] = True
    if overrides:
        settings = replace(settings, **overrides)

    try:
        kind = detect_source_kind(args.source)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if kind is SourceKind.MEDIA_FILE or (
        kind is SourceKind.YOUTUBE and settings.youtube_local_transcribe
    ):
        print(
            f"Transcribing with {settings.transcription_backend} "
            f"({settings.whisper_model})…",
            file=sys.stderr,
        )

    extractor = extractor_for(kind, settings)
    try:
        transcript = extractor.extract(args.source)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Failed to extract text: {e}", file=sys.stderr)
        return 1

    if kind is SourceKind.YOUTUBE and not settings.youtube_local_transcribe:
        vtt_candidates = sorted(Path(".").glob(settings.transcript_glob))
        if vtt_candidates:
            print(f"Using subtitles: {vtt_candidates[0]}", file=sys.stderr)

    chunks = smart_chunk(transcript, settings.chunk_chars)
    print(
        f"Transcript length: {len(transcript):,} chars | chunks: {len(chunks)}",
        file=sys.stderr,
    )

    part_summaries: list[str] = []
    for i, ch in enumerate(chunks, 1):
        print(
            f"Summarizing chunk {i}/{len(chunks)} with {settings.chunk_model}...",
            file=sys.stderr,
        )
        chunk_summary = summarize_chunk(ch, settings)
        if not chunk_summary:
            print(f"Failed to summarize chunk {i}.", file=sys.stderr)
            return 1
        part_summaries.append(chunk_summary)

    print(
        f"Creating final summary with {settings.final_model}...",
        file=sys.stderr,
    )
    summary = finalize_summary(part_summaries, settings)
    if not summary:
        print("Final summary is empty.", file=sys.stderr)
        return 1

    if args.output is None or args.output == "-":
        print(summary)
    else:
        out_path = Path(args.output)
        out_path.write_text(summary, encoding="utf-8")
        print(f"Wrote summary to: {out_path.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
