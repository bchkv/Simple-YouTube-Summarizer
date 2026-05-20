from openai import OpenAI

from summarizer.config import Settings, DEFAULT_SETTINGS

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _chat_create(client: OpenAI, model: str, messages: list[dict], temperature: float):
    kwargs = {
        "model": model,
        "messages": messages,
    }
    if not model.startswith("gpt-5"):
        kwargs["temperature"] = temperature
    return client.chat.completions.create(**kwargs)


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
