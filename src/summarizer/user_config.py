"""User-wide config under ~/.config/summarizer/.env."""

from __future__ import annotations

import os
import re
import sys
from getpass import getpass
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "summarizer"
CONFIG_FILE = CONFIG_DIR / ".env"

_KEY_VAR = "OPENAI_API_KEY"
_KEY_PATTERN = re.compile(
    r"^(?P<name>OPENAI_API_KEY)\s*=\s*(?P<value>.*)$",
    re.MULTILINE,
)


def mask_api_key(key: str) -> str:
    key = key.strip()
    if len(key) <= 8:
        return "***"
    return f"{key[:7]}…{key[-4:]}"


def api_key_is_set() -> bool:
    value = os.getenv(_KEY_VAR)
    return bool(value and value.strip())


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_DIR.chmod(0o700)
    except OSError:
        pass


def _read_config_lines() -> list[str]:
    if not CONFIG_FILE.is_file():
        return []
    return CONFIG_FILE.read_text(encoding="utf-8").splitlines()


def _write_config_lines(lines: list[str]) -> None:
    _ensure_config_dir()
    body = "\n".join(lines)
    if body:
        body += "\n"
    CONFIG_FILE.write_text(body, encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def set_api_key(*, key: str | None = None) -> Path:
    if key is None:
        key = getpass("OpenAI API key: ").strip()
    if not key:
        raise SystemExit("No key entered.")

    lines = _read_config_lines()
    out: list[str] = []
    replaced = False
    for line in lines:
        if _KEY_PATTERN.match(line):
            if not replaced:
                out.append(f"{_KEY_VAR}={key}")
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(f"{_KEY_VAR}={key}")

    _write_config_lines(out)
    return CONFIG_FILE


def unset_api_key() -> bool:
    if not CONFIG_FILE.is_file():
        return False

    lines = _read_config_lines()
    kept = [line for line in lines if not _KEY_PATTERN.match(line)]
    if len(kept) == len(lines):
        return False

    if kept:
        _write_config_lines(kept)
    else:
        CONFIG_FILE.unlink(missing_ok=True)
    return True


def read_stored_api_key() -> str | None:
    if not CONFIG_FILE.is_file():
        return None
    for line in _read_config_lines():
        match = _KEY_PATTERN.match(line)
        if match:
            value = match.group("value").strip().strip('"').strip("'")
            return value or None
    return None


def config_show_message() -> str:
    env_key = os.getenv(_KEY_VAR)
    file_key = read_stored_api_key()

    lines = [f"Config file: {CONFIG_FILE}"]
    if env_key and env_key.strip():
        lines.append(
            f"OPENAI_API_KEY (environment): {mask_api_key(env_key)}"
        )
    else:
        lines.append("OPENAI_API_KEY (environment): not set")

    if file_key:
        lines.append(
            f"OPENAI_API_KEY (config file): {mask_api_key(file_key)}"
        )
    else:
        lines.append("OPENAI_API_KEY (config file): not set")

    if api_key_is_set():
        lines.append("Effective key: set (environment or loaded config)")
    else:
        lines.append("Effective key: not set")
    return "\n".join(lines)


def missing_api_key_message() -> str:
    return (
        "OpenAI API key is not set.\n"
        "Set one with:\n"
        "  summarize config set-key\n"
        "Or export manually:\n"
        '  export OPENAI_API_KEY="sk-..."\n'
        f"User config file: {CONFIG_FILE}"
    )


def config_main(argv: list[str]) -> int:
    if not argv:
        print(
            "Usage: summarize config {set-key, path, show, unset-key}",
            file=sys.stderr,
        )
        return 2

    cmd = argv[0]
    if cmd == "set-key":
        path = set_api_key()
        print(f"Saved API key to {path}")
        return 0
    if cmd == "path":
        print(CONFIG_FILE)
        return 0
    if cmd == "show":
        print(config_show_message())
        return 0
    if cmd == "unset-key":
        if unset_api_key():
            print(f"Removed API key from {CONFIG_FILE}")
        else:
            print(f"No API key in {CONFIG_FILE}")
        return 0

    print(f"Unknown config command: {cmd}", file=sys.stderr)
    print(
        "Usage: summarize config {set-key, path, show, unset-key}",
        file=sys.stderr,
    )
    return 2
