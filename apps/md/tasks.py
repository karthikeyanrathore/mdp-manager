from celery import shared_task

from .embedder import embed_texts
from .models import Markdown


@shared_task(bind=True, max_retries=3)
def embed_markdown(self, markdown_id):
    """Embed a markdown's full text and persist the vector."""
    markdown = Markdown.objects.get(pk=markdown_id)
    markdown.status = Markdown.Status.PROCESSING
    markdown.save(update_fields=["status"])

    try:
        markdown.embedding = embed_texts([markdown.text])[0]
        markdown.status = Markdown.Status.DONE
        markdown.error = ""
        markdown.save(update_fields=["embedding", "status", "error"])
    except Exception as exc:
        markdown.status = Markdown.Status.FAILED
        markdown.error = str(exc)
        markdown.save(update_fields=["status", "error"])
        raise self.retry(exc=exc, countdown=10)

    return {"markdown_id": str(markdown_id)}
