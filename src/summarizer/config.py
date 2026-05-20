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
load_dotenv(dotenv_path=_REPO_ROOT / ".env", override=True)


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


def _default_whisper_model(backend: str) -> str:
    explicit = _env("SUMMARIZER_WHISPER_MODEL")
    if explicit:
        return explicit
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


def load_settings(*, transcribe: bool = False) -> Settings:
    backend = _default_transcription_backend()
    whisper_model = _default_whisper_model(backend)
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
        whisper_model=whisper_model,
        whisper_device=whisper_device,
        whisper_compute_type=whisper_compute_type,
        transcribe_language=transcribe_language,
        use_transcribe=transcribe or bool(_env_bool("SUMMARIZER_USE_TRANSCRIBE")),
    )


DEFAULT_SETTINGS = load_settings()
