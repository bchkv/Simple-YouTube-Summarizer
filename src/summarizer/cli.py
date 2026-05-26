import argparse
import sys
from pathlib import Path

from summarizer.config import load_environment, load_settings
from summarizer.pipeline import summarize_transcript, smart_chunk
from summarizer.routing import SourceKind, detect_source_kind, extractor_for
from summarizer.user_config import api_key_is_set, config_main, missing_api_key_message


def _log(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr)


def _write_output(text: str, output: str | None, *, quiet: bool) -> None:
    if output is None or output == "-":
        print(text)
        return

    out_path = Path(output)
    out_path.write_text(text, encoding="utf-8")
    _log(f"Wrote output to: {out_path.resolve()}", quiet=quiet)


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


def _summarize_main(argv: list[str]) -> int:
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
        help="Write output to this file instead of stdout",
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
        "--transcript",
        action="store_true",
        help="Print the extracted full transcript and skip summarization",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print the final output (suppress progress logs)",
    )
    args = parser.parse_args(argv)

    load_environment()
    if not args.transcript and not api_key_is_set():
        print(missing_api_key_message(), file=sys.stderr)
        return 2

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

    if args.transcript:
        _write_output(transcript, args.output, quiet=quiet)
        return 0

    _log(f"Summarizing with {settings.final_model}…", quiet=quiet)
    try:
        summary = summarize_transcript(transcript, settings)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    if not summary:
        print("Summary is empty.", file=sys.stderr)
        return 1

    _write_output(summary, args.output, quiet=quiet)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "config":
        load_environment()
        return config_main(argv[1:])
    return _summarize_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
