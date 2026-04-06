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
    # GPT-5 chat models currently only accept default temperature behavior.
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


def summarize_chunk(chunk: str, settings: Settings = DEFAULT_SETTINGS) -> str:
    client = _get_client()
    messages = [
            {
                "role": "system",
                "content": (
                    "You summarize technical transcripts faithfully. "
                    "Do not add information that is not stated."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize this transcript chunk focusing on technical fidelity:\n"
                    "- Concepts/definitions introduced\n"
                    "- Steps/algorithms/procedures described\n"
                    "- Parameters, numbers, units\n"
                    "- Assumptions, caveats, trade-offs\n\n"
                    "Return concise bullets.\n\n"
                    f"CHUNK:\n{chunk}"
                ),
            },
        ]
    resp = _chat_create(client, settings.chunk_model, messages, temperature=0.2)

    content = resp.choices[0].message.content
    return content.strip() if content else ""


def finalize_summary(
    part_summaries: list[str],
    settings: Settings = DEFAULT_SETTINGS,
) -> str:
    client = _get_client()
    combined = "\n\n".join(
        f"Part {i + 1} summary:\n{summ}"
        for i, summ in enumerate(part_summaries)
    )

    messages = [
            {
                "role": "system",
                "content": (
                    "You produce clear, accurate summaries. "
                    "Avoid speculation."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Combine these part-summaries into one clean, regular summary.\n"
                    "Write 2-4 short paragraphs in plain language.\n"
                    "If useful, end with up to 3 concise bullet points for key takeaways.\n"
                    "Do not add section headings.\n"
                    "Do not add follow-up questions, offers, or extra commentary.\n\n"
                    f"{combined}"
                ),
            },
        ]
    resp = _chat_create(client, settings.final_model, messages, temperature=0.7)

    content = resp.choices[0].message.content
    return content.strip() if content else ""
