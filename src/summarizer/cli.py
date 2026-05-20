import argparse
import sys
from pathlib import Path

from summarizer.config import load_settings
from summarizer.pipeline import summarize_transcript, smart_chunk
from summarizer.routing import SourceKind, detect_source_kind, extractor_for


def _log(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr)


def _extract_transcript(
    source: str,
    kind: SourceKind,
    settings,
    *,
    quiet: bool,
) -> str:
    if kind is SourceKind.MEDIA_FILE:
        from summarizer.extractors.media_file import MediaFileExtractor

        _log(
            f"Transcribing with {settings.transcription_backend} "
            f"({settings.whisper_model})…",
            quiet=quiet,
        )
        return MediaFileExtractor(settings).extract(source, quiet=quiet)

    if kind is SourceKind.YOUTUBE:
        from summarizer.extractors.youtube import YouTubeExtractor

        return YouTubeExtractor(settings).extract(source, quiet=quiet)

    if kind is SourceKind.PDF_FILE:
        from summarizer.extractors.pdf_file import PdfFileExtractor

        return PdfFileExtractor(settings).extract(source, quiet=quiet)

    return extractor_for(kind, settings).extract(source)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize YouTube videos, PDFs, local media, or text files.",
    )
    parser.add_argument(
        "source",
        help="YouTube URL or path to a PDF, text, audio, or video file",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=None,
        help="Write summary to this file instead of stdout",
    )
    parser.add_argument(
        "--transcribe",
        action="store_true",
        help=(
            "Use on-device speech-to-text "
            "(YouTube: skip captions; media: always transcribe)"
        ),
    )
    parser.add_argument(
        "-m",
        "--whisper-model",
        metavar="SIZE",
        default=None,
        help=(
            "Whisper model for --transcribe: tiny, base, small, medium, "
            "large-v3, turbo, distil-large-v3 (aliases: large, big). "
            "Or a full model id / Hugging Face repo."
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print the summary (suppress progress logs)",
    )
    args = parser.parse_args(argv)

    settings = load_settings(
        transcribe=args.transcribe,
        whisper_model=args.whisper_model,
    )
    quiet = args.quiet

    try:
        kind = detect_source_kind(args.source)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    try:
        transcript = _extract_transcript(
            args.source, kind, settings, quiet=quiet
        )
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Failed to extract text: {e}", file=sys.stderr)
        return 1

    if (
        not quiet
        and settings.use_transcribe
        and len(transcript) < 500
    ):
        print(
            "Warning: transcript looks very short; audio may be incomplete. "
            "Ensure ffmpeg is installed for YouTube audio extraction.",
            file=sys.stderr,
        )

    chunks = smart_chunk(transcript, settings.chunk_chars)
    _log(
        f"Transcript length: {len(transcript):,} chars | chunks: {len(chunks)}",
        quiet=quiet,
    )

    _log(f"Summarizing with {settings.final_model}…", quiet=quiet)
    summary = summarize_transcript(transcript, settings)
    if not summary:
        print("Summary is empty.", file=sys.stderr)
        return 1

    if args.output is None or args.output == "-":
        print(summary)
    else:
        out_path = Path(args.output)
        out_path.write_text(summary, encoding="utf-8")
        _log(f"Wrote summary to: {out_path.resolve()}", quiet=quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
