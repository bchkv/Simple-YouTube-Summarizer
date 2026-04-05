from openai import OpenAI

from summarizer.config import Settings, DEFAULT_SETTINGS

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


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
    resp = client.chat.completions.create(
        model=settings.chunk_model,
        messages=[
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
        ],
        temperature=0.2,
    )

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

    resp = client.chat.completions.create(
        model=settings.final_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You produce clear, technically accurate synthesis. "
                    "Avoid speculation."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Combine these part-summaries into a final technical summary with:\n"
                    "1) Overview (3–6 sentences)\n"
                    "2) Technical breakdown (sections with headings)\n"
                    "3) Key parameters / numbers / equations mentioned (if any)\n"
                    "4) Assumptions, limitations, trade-offs\n"
                    "5) Practical takeaways / recommended actions (if any)\n\n"
                    f"{combined}"
                ),
            },
        ],
        temperature=0.7,
    )

    content = resp.choices[0].message.content
    return content.strip() if content else ""
