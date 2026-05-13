from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    start_char: int
    end_char: int


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 180) -> list[TextChunk]:
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not cleaned:
        return []

    chunks: list[TextChunk] = []
    start = 0
    text_length = len(cleaned)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        end = target_end

        if target_end < text_length:
            paragraph_break = cleaned.rfind("\n\n", start, target_end)
            sentence_break = cleaned.rfind(". ", start, target_end)
            if paragraph_break > start + chunk_size // 2:
                end = paragraph_break
            elif sentence_break > start + chunk_size // 2:
                end = sentence_break + 1

        content = cleaned[start:end].strip()
        if content:
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=content,
                    start_char=start,
                    end_char=end,
                )
            )

        if end >= text_length:
            break
        start = max(0, end - overlap)

    return chunks
