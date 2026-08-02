from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_model():
    """Load the SentenceTransformer once per process (~90 MB)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def embed_texts(texts):
    """Embed a batch of strings into a list of float vectors."""
    if not texts:
        return []
    vectors = get_model().encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]
