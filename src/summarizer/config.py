import os
import platform
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    # Keep CLI usable even if optional dotenv isn't installed.
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_ENV = _REPO_ROOT / ".env"

_ENV_LOADED = False


def load_environment() -> None:
    """Load API key and settings from user config, then project .env."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    from summarizer.user_config import CONFIG_FILE

    load_dotenv(dotenv_path=CONFIG_FILE, override=False)
    load_dotenv(dotenv_path=_PROJECT_ENV, override=True)
    _ENV_LOADED = True


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_bool(name: str) -> bool | None:
    raw = _env(name)
    if raw is None:
        return None
    return raw.lower() in ("1", "true", "yes", "on")


def _cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _default_transcription_backend() -> str:
    explicit = _env("SUMMARIZER_TRANSCRIPTION_BACKEND")
    if explicit:
        return explicit
    try:
        import faster_whisper  # noqa: F401

        return "faster_whisper"
    except ImportError:
        pass
    try:
        import mlx_whisper  # noqa: F401

        if platform.machine().lower() in ("arm64", "aarch64"):
            return "mlx_whisper"
    except ImportError:
        pass
    return "faster_whisper"


def _default_whisper_device(backend: str) -> str:
    explicit = _env("SUMMARIZER_WHISPER_DEVICE")
    if explicit:
        return explicit
    key = backend.lower().replace("-", "_")
    if key in ("faster_whisper", "faster") and _cuda_available():
        return "cuda"
    return "cpu"


def _default_whisper_compute_type(backend: str, device: str) -> str:
    explicit = _env("SUMMARIZER_WHISPER_COMPUTE_TYPE")
    if explicit:
        return explicit
    if device == "cuda":
        return "float16"
    return "int8"


_WHISPER_ALIASES: dict[str, str] = {
    "big": "large-v3",
    "large": "large-v3",
}

_FASTER_WHISPER_SIZES = frozenset(
    {
        "tiny",
        "base",
        "small",
        "medium",
        "large-v1",
        "large-v2",
        "large-v3",
        "large",
        "distil-large-v3",
        "turbo",
    }
)

_MLX_WHISPER_MODELS: dict[str, str] = {
    "tiny": "mlx-community/whisper-tiny",
    "base": "mlx-community/whisper-small",
    "small": "mlx-community/whisper-small",
    "medium": "mlx-community/whisper-medium",
    "large-v1": "mlx-community/whisper-large-v1",
    "large-v2": "mlx-community/whisper-large-v2",
    "large-v3": "mlx-community/whisper-large-v3",
    "large": "mlx-community/whisper-large-v3",
    "big": "mlx-community/whisper-large-v3",
    "turbo": "mlx-community/whisper-large-v3-turbo",
    "distil-large-v3": "mlx-community/whisper-large-v3",
}


def resolve_whisper_model(name: str | None, backend: str) -> str:
    """Map CLI/env size aliases to backend-specific model ids."""
    if not name:
        return _default_whisper_model(backend)

    raw = name.strip()
    if "/" in raw:
        return raw

    key = _WHISPER_ALIASES.get(raw.lower(), raw.lower())
    backend_key = backend.lower().replace("-", "_")

    if backend_key in ("faster_whisper", "faster"):
        if key in _FASTER_WHISPER_SIZES or key in _WHISPER_ALIASES:
            return key
        return raw

    if backend_key in ("mlx_whisper", "mlx"):
        if key in _MLX_WHISPER_MODELS:
            return _MLX_WHISPER_MODELS[key]
        return f"mlx-community/whisper-{key}"

    return raw


def _default_whisper_model(backend: str) -> str:
    explicit = _env("SUMMARIZER_WHISPER_MODEL")
    if explicit:
        return resolve_whisper_model(explicit, backend)
    key = backend.lower().replace("-", "_")
    if key in ("faster_whisper", "faster"):
        return "base"
    return "mlx-community/whisper-tiny"


@dataclass(frozen=True)
class Settings:
    chunk_model: str = "gpt-4o-mini"
    final_model: str = "gpt-5-mini"
    # None = auto-pick YouTube *-orig captions (e.g. ru-orig, en-orig)
    sub_lang: str | None = None
    chunk_chars: int = 9000
    transcript_glob: str = "transcript*.vtt"
    transcription_backend: str = "faster_whisper"
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    transcribe_language: str | None = None
    # CLI --transcribe: skip YouTube captions; use on-device STT instead
    use_transcribe: bool = False
    pdf_ocr_dpi: int = 200
    pdf_ocr_language: str | None = None
    pdf_force_ocr: bool = False


def load_settings(
    *,
    transcribe: bool = False,
    whisper_model: str | None = None,
) -> Settings:
    load_environment()
    backend = _default_transcription_backend()
    chosen_model = whisper_model or _env("SUMMARIZER_WHISPER_MODEL")
    resolved_model = resolve_whisper_model(chosen_model, backend)
    whisper_device = _default_whisper_device(backend)
    whisper_compute_type = _default_whisper_compute_type(backend, whisper_device)
    sub_lang = _env("SUMMARIZER_SUB_LANG")
    transcribe_language = _env("SUMMARIZER_TRANSCRIBE_LANGUAGE")

    chunk_model = _env("SUMMARIZER_CHUNK_MODEL") or Settings.chunk_model
    final_model = _env("SUMMARIZER_FINAL_MODEL") or Settings.final_model
    chunk_chars_raw = _env("SUMMARIZER_CHUNK_CHARS")
    chunk_chars = int(chunk_chars_raw) if chunk_chars_raw else Settings.chunk_chars

    return Settings(
        chunk_model=chunk_model,
        final_model=final_model,
        sub_lang=sub_lang if sub_lang else None,
        chunk_chars=chunk_chars,
        transcript_glob=_env("SUMMARIZER_TRANSCRIPT_GLOB") or Settings.transcript_glob,
        transcription_backend=backend,
        whisper_model=resolved_model,
        whisper_device=whisper_device,
        whisper_compute_type=whisper_compute_type,
        transcribe_language=transcribe_language,
        use_transcribe=transcribe or bool(_env_bool("SUMMARIZER_USE_TRANSCRIBE")),
        pdf_ocr_dpi=int(_env("SUMMARIZER_PDF_OCR_DPI") or "200"),
        pdf_ocr_language=_env("SUMMARIZER_PDF_OCR_LANGUAGE"),
        pdf_force_ocr=bool(_env_bool("SUMMARIZER_PDF_FORCE_OCR")),
    )


DEFAULT_SETTINGS = load_settings()
