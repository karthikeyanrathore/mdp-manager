from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from .chunking import chunk_text
from .models import Chunk, Markdown, Project


class ChunkTextTests(TestCase):
    def test_short_text_single_chunk(self):
        assert chunk_text("hello world") == ["hello world"]

    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   \n  ") == []

    def test_overlap_between_chunks(self):
        words = " ".join(str(i) for i in range(10))
        chunks = chunk_text(words, chunk_size=4, overlap=2)
        # step = 2 → chunks start at 0,2,4,6 (8 would be tail of prev)
        assert chunks[0] == "0 1 2 3"
        assert chunks[1] == "2 3 4 5"  # 2-word overlap with previous
        assert chunks[-1].split()[-1] == "9"

    def test_invalid_overlap(self):
        with self.assertRaises(ValueError):
            chunk_text("a b c", chunk_size=2, overlap=2)


# Fake embedder so tests don't download / run the real model.
def _fake_embed_texts(texts):
    return [[float(len(t))] * 384 for t in texts]


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class MarkdownApiTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="proj-a")

    @patch("embeddings.tasks.embed_texts", side_effect=_fake_embed_texts)
    def test_create_markdown_runs_embedding(self, _mock):
        resp = self.client.post(
            "/api/markdowns/",
            {
                "project": str(self.project.id),
                "title": "t",
                "text": "one two three four five six",
            },
            format="json",
        )
        assert resp.status_code == 202, resp.content
        doc_id = resp.data["id"]

        doc = Markdown.objects.get(pk=doc_id)
        assert doc.project_id == self.project.id
        assert doc.status == Markdown.Status.DONE
        assert Chunk.objects.filter(markdown=doc).count() >= 1

    def test_create_markdown_requires_project(self):
        resp = self.client.post(
            "/api/markdowns/",
            {"text": "no project here"},
            format="json",
        )
        assert resp.status_code == 400

    @patch("embeddings.tasks.embed_texts", side_effect=_fake_embed_texts)
    def test_upload_md_file(self, _mock):
        upload = SimpleUploadedFile(
            "note.md", b"# Title\n\nsome markdown body", content_type="text/markdown"
        )
        resp = self.client.post(
            "/api/markdowns/upload/",
            {"file": upload, "project": str(self.project.id)},
            format="multipart",
        )
        assert resp.status_code == 202, resp.content
        doc = Markdown.objects.get(pk=resp.data["id"])
        assert doc.title == "note.md"
        assert doc.project_id == self.project.id
        assert doc.status == Markdown.Status.DONE
        assert Chunk.objects.filter(markdown=doc).count() >= 1

    def test_upload_rejects_non_md(self):
        upload = SimpleUploadedFile("note.txt", b"plain", content_type="text/plain")
        resp = self.client.post(
            "/api/markdowns/upload/",
            {"file": upload, "project": str(self.project.id)},
            format="multipart",
        )
        assert resp.status_code == 400

    def test_create_project_via_api(self):
        resp = self.client.post("/api/projects/", {"name": "proj-b"}, format="json")
        assert resp.status_code == 201, resp.content
        assert Project.objects.filter(name="proj-b").exists()

    @patch("embeddings.views.embed_texts", side_effect=_fake_embed_texts)
    @patch("embeddings.tasks.embed_texts", side_effect=_fake_embed_texts)
    def test_search_scoped_to_project(self, _t, _v):
        other = Project.objects.create(name="proj-other")
        self.client.post(
            "/api/markdowns/",
            {"project": str(self.project.id), "text": "alpha beta gamma delta"},
            format="json",
        )

        # Search within the project that has chunks → results.
        resp = self.client.post(
            "/api/search/",
            {"query": "alpha", "project": str(self.project.id), "top_k": 3},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        assert len(resp.data) >= 1
        assert "distance" in resp.data[0]

        # Search within a different project → none of those chunks.
        resp = self.client.post(
            "/api/search/",
            {"query": "alpha", "project": str(other.id), "top_k": 3},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        assert resp.data == []
