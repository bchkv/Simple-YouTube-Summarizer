#!/usr/bin/env python3
"""Backward-compatible entry: run the CLI without an editable install."""

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from summarizer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
