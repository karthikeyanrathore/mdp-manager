import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.core.models import Project
from apps.routing.models import RoutingPolicy

from .models import Markdown


# Fake embedder so tests don't download / run the real model.
def _fake_embed_texts(texts):
    return [[float(len(t))] * 384 for t in texts]


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class MarkdownApiTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="proj-a")

    @patch("apps.md.tasks.embed_texts", side_effect=_fake_embed_texts)
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
        assert doc.embedding is not None

    def test_create_markdown_requires_project(self):
        resp = self.client.post(
            "/api/markdowns/",
            {"text": "no project here"},
            format="json",
        )
        assert resp.status_code == 400

    @patch("apps.md.tasks.embed_texts", side_effect=_fake_embed_texts)
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
        assert doc.embedding is not None

    def test_upload_rejects_non_md(self):
        upload = SimpleUploadedFile("note.txt", b"plain", content_type="text/plain")
        resp = self.client.post(
            "/api/markdowns/upload/",
            {"file": upload, "project": str(self.project.id)},
            format="multipart",
        )
        assert resp.status_code == 400


class MarkdownRoutingPolicyTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="proj-a")
        self.markdown = Markdown.objects.create(
            project=self.project, title="doc", text="body"
        )
        self.url = f"/api/markdowns/{self.markdown.id}/routing-policy/"

    def make_policy(self, name, created_at, project=None):
        policy = RoutingPolicy.objects.create(
            project=project or self.project, name=name
        )
        # created_at is auto_now_add, so it has to be forced after the fact to
        # make the selection rule deterministic.
        RoutingPolicy.objects.filter(pk=policy.pk).update(created_at=created_at)
        return policy

    def test_returns_a_single_policy_not_a_list(self):
        self.make_policy("only", datetime(2026, 1, 1, tzinfo=timezone.utc))

        resp = self.client.get(self.url)
        assert resp.status_code == 200, resp.content
        assert resp.data["name"] == "only"
        assert resp.data["project"] == self.project.id
        # A single object, not paginated.
        assert "results" not in resp.data
        assert "count" not in resp.data

    def test_selects_one_of_several_policies(self):
        self.make_policy("older", datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.make_policy("newer", datetime(2026, 6, 1, tzinfo=timezone.utc))

        resp = self.client.get(self.url)
        assert resp.status_code == 200, resp.content
        # Current placeholder rule in apps/routing/selection.py: newest wins.
        assert resp.data["name"] == "newer"

    def test_never_selects_a_policy_from_another_project(self):
        other = Project.objects.create(name="proj-other")
        self.make_policy("mine", datetime(2026, 1, 1, tzinfo=timezone.utc))
        # Newer, but belongs to a different project.
        self.make_policy(
            "theirs", datetime(2026, 6, 1, tzinfo=timezone.utc), project=other
        )

        resp = self.client.get(self.url)
        assert resp.status_code == 200, resp.content
        assert resp.data["name"] == "mine"

    def test_404_when_project_has_no_policies(self):
        resp = self.client.get(self.url)
        assert resp.status_code == 404

    def test_unknown_markdown_is_404(self):
        resp = self.client.get(f"/api/markdowns/{uuid.uuid4()}/routing-policy/")
        assert resp.status_code == 404
