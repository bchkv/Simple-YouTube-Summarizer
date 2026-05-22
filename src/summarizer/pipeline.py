from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI

from summarizer.config import Settings, DEFAULT_SETTINGS
from summarizer.user_config import missing_api_key_message

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.strip():
            raise RuntimeError(missing_api_key_message())
        _client = OpenAI(api_key=api_key)
    return _client


def _chat_create(client: OpenAI, model: str, messages: list[dict], temperature: float):
    kwargs = {
        "model": model,
        "messages": messages,
    }
    if not model.startswith("gpt-5"):
        kwargs["temperature"] = temperature
    try:
        return client.chat.completions.create(**kwargs)
    except AuthenticationError as e:
        raise RuntimeError(
            "OpenAI authentication failed.\n"
            "Set a valid API key with:\n"
            "  summarize config set-key\n"
            "Or export it manually:\n"
            '  export OPENAI_API_KEY="sk-..."'
        ) from e
    except APIStatusError as e:
        if e.status_code == 401:
            raise RuntimeError(
                "OpenAI authentication failed.\n"
                "Set a valid API key with:\n"
                "  summarize config set-key\n"
                "Or export it manually:\n"
                '  export OPENAI_API_KEY="sk-..."'
            ) from e
        raise
    except APIConnectionError:
        raise


def smart_chunk(text: str, limit: int) -> list[str]:
    chunks: list[str] = []
    t = text.strip()

    while len(t) > limit:
        cut = t.rfind("\n", 0, limit)
        if cut == -1:
            cut = t.rfind(". ", 0, limit)
        if cut == -1:
            cut = limit

        chunks.append(t[:cut].strip())
        t = t[cut:].strip()

    if t:
        chunks.append(t)

    return chunks


def _summarize(text: str, settings: Settings) -> str:
    client = _get_client()
    messages = [{"role": "user", "content": f"Summarize:\n\n{text}"}]
    resp = _chat_create(client, settings.final_model, messages, temperature=0.3)
    content = resp.choices[0].message.content
    return content.strip() if content else ""


def summarize_transcript(text: str, settings: Settings = DEFAULT_SETTINGS) -> str:
    chunks = smart_chunk(text, settings.chunk_chars)
    if len(chunks) == 1:
        return _summarize(chunks[0], settings)
    partials = [_summarize(chunk, settings) for chunk in chunks]
    return _summarize("\n\n".join(partials), settings)
