import re


def chunk_text(text, chunk_size=500, overlap=50):
    """Split ``text`` into word-count chunks with overlap.

    Splits on whitespace and greedily packs words into chunks of at most
    ``chunk_size`` words. Consecutive chunks share the last ``overlap`` words of
    the previous chunk so context is not lost at boundaries.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    words = re.split(r"\s+", text.strip())
    words = [w for w in words if w]
    if not words:
        return []

    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks
