import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField


class Markdown(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title or self.id} ({self.status})"


class Chunk(models.Model):
    markdown = models.ForeignKey(
        Markdown, related_name="chunks", on_delete=models.CASCADE
    )
    index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("markdown", "index")
        ordering = ["markdown", "index"]

    def __str__(self):
        return f"{self.markdown_id}#{self.index}"
