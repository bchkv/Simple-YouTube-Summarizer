import argparse
import sys
from pathlib import Path

from summarizer.config import DEFAULT_SETTINGS, Settings
from summarizer.pipeline import finalize_summary, smart_chunk, summarize_chunk
from summarizer.routing import SourceKind, detect_source_kind, extractor_for


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize YouTube videos (subtitles) or plain text files.",
    )
    parser.add_argument(
        "source",
        help="YouTube URL or path to a .txt / .md (UTF-8) file",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=None,
        help=f"Write summary here (default: {DEFAULT_SETTINGS.summary_file})",
    )
    args = parser.parse_args(argv)

    settings = Settings()
    out_path = Path(args.output or settings.summary_file)

    try:
        kind = detect_source_kind(args.source)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    extractor = extractor_for(kind, settings)
    try:
        transcript = extractor.extract(args.source)
    except (FileNotFoundError, RuntimeError) as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Failed to extract text: {e}", file=sys.stderr)
        return 1

    if kind is SourceKind.YOUTUBE:
        # VTT path is under cwd from yt-dlp; name is stable for transcript.*.vtt
        vtt_candidates = sorted(Path(".").glob(settings.transcript_glob))
        if vtt_candidates:
            print(f"Using subtitles: {vtt_candidates[0]}")

    chunks = smart_chunk(transcript, settings.chunk_chars)
    print(f"Transcript length: {len(transcript):,} chars | chunks: {len(chunks)}")

    part_summaries: list[str] = []
    for i, ch in enumerate(chunks, 1):
        print(f"Summarizing chunk {i}/{len(chunks)} with {settings.chunk_model}...")
        summary = summarize_chunk(ch, settings)
        if not summary:
            print(f"Failed to summarize chunk {i}.", file=sys.stderr)
            return 1
        part_summaries.append(summary)

    print(f"Creating final summary with {settings.final_model}...")
    summary = finalize_summary(part_summaries, settings)
    if not summary:
        print("Final summary is empty.", file=sys.stderr)
        return 1

    out_path.write_text(summary, encoding="utf-8")
    print(f"Saved summary to: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
