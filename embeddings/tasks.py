from celery import shared_task

from .chunking import chunk_text
from .embedder import embed_texts
from .models import Chunk, Markdown


@shared_task(bind=True, max_retries=3)
def embed_markdown(self, markdown_id):
    """Chunk a markdown's text, embed each chunk, and persist the vectors."""
    markdown = Markdown.objects.get(pk=markdown_id)
    markdown.status = Markdown.Status.PROCESSING
    markdown.save(update_fields=["status"])

    try:
        chunks = chunk_text(markdown.text)
        vectors = embed_texts(chunks)

        Chunk.objects.filter(markdown=markdown).delete()
        Chunk.objects.bulk_create(
            [
                Chunk(markdown=markdown, index=i, text=text, embedding=vector)
                for i, (text, vector) in enumerate(zip(chunks, vectors))
            ]
        )

        markdown.status = Markdown.Status.DONE
        markdown.error = ""
        markdown.save(update_fields=["status", "error"])
    except Exception as exc:
        markdown.status = Markdown.Status.FAILED
        markdown.error = str(exc)
        markdown.save(update_fields=["status", "error"])
        raise self.retry(exc=exc, countdown=10)

    return {"markdown_id": str(markdown_id), "chunks": len(chunks)}
