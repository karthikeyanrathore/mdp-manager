from rest_framework.test import APITestCase

from apps.routing.models import RoutingPolicy

from .models import Project


class ProjectApiTests(APITestCase):
    def test_create_project_via_api(self):
        resp = self.client.post("/api/projects/", {"name": "proj-b"}, format="json")
        assert resp.status_code == 201, resp.content
        assert Project.objects.filter(name="proj-b").exists()

    def test_project_reports_related_counts(self):
        project = Project.objects.create(name="proj-counts")
        RoutingPolicy.objects.create(project=project, name="p1")
        RoutingPolicy.objects.create(project=project, name="p2")

        resp = self.client.get(f"/api/projects/{project.id}/")
        assert resp.status_code == 200, resp.content
        assert resp.data["routing_policy_count"] == 2
        assert resp.data["markdown_count"] == 0
