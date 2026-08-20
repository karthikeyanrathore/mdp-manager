import uuid

from rest_framework.test import APITestCase

from apps.core.models import Project

from .models import RoutingPolicy


class RoutingPolicyApiTests(APITestCase):
    def setUp(self):
        self.project = Project.objects.create(name="proj-a")
        self.url = f"/api/projects/{self.project.id}/routing-policies/"

    def detail_url(self, policy):
        return f"/api/projects/{self.project.id}/routing-policies/{policy.id}/"

    def test_create_routing_policy(self):
        resp = self.client.post(
            self.url,
            {"name": "eu-west", "description": "Route EU traffic west"},
            format="json",
        )
        assert resp.status_code == 201, resp.content
        policy = RoutingPolicy.objects.get(pk=resp.data["id"])
        assert policy.name == "eu-west"
        assert policy.description == "Route EU traffic west"
        assert policy.project_id == self.project.id
        assert resp.data["project"] == self.project.id

    def test_create_requires_name(self):
        resp = self.client.post(self.url, {"description": "no name"}, format="json")
        assert resp.status_code == 400

    def test_description_is_optional(self):
        resp = self.client.post(self.url, {"name": "minimal"}, format="json")
        assert resp.status_code == 201, resp.content
        assert RoutingPolicy.objects.get(pk=resp.data["id"]).description == ""

    def test_name_unique_within_project(self):
        RoutingPolicy.objects.create(project=self.project, name="dup")
        resp = self.client.post(self.url, {"name": "dup"}, format="json")
        assert resp.status_code == 400, resp.content

    def test_same_name_allowed_in_different_projects(self):
        other = Project.objects.create(name="proj-other")
        RoutingPolicy.objects.create(project=other, name="shared")

        resp = self.client.post(self.url, {"name": "shared"}, format="json")
        assert resp.status_code == 201, resp.content
        assert RoutingPolicy.objects.filter(name="shared").count() == 2

    def test_rename_onto_existing_name_is_rejected(self):
        RoutingPolicy.objects.create(project=self.project, name="taken")
        policy = RoutingPolicy.objects.create(project=self.project, name="orig")

        resp = self.client.patch(
            self.detail_url(policy), {"name": "taken"}, format="json"
        )
        assert resp.status_code == 400, resp.content

    def test_patch_keeping_own_name_is_allowed(self):
        policy = RoutingPolicy.objects.create(project=self.project, name="keep")
        resp = self.client.patch(
            self.detail_url(policy),
            {"name": "keep", "description": "updated"},
            format="json",
        )
        assert resp.status_code == 200, resp.content

    def test_list_is_scoped_to_project(self):
        other = Project.objects.create(name="proj-other")
        RoutingPolicy.objects.create(project=self.project, name="mine")
        RoutingPolicy.objects.create(project=other, name="theirs")

        resp = self.client.get(self.url)
        assert resp.status_code == 200, resp.content
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["name"] == "mine"

    def test_unknown_project_is_404(self):
        resp = self.client.get(f"/api/projects/{uuid.uuid4()}/routing-policies/")
        assert resp.status_code == 404

    def test_policy_from_another_project_is_404(self):
        other = Project.objects.create(name="proj-other")
        policy = RoutingPolicy.objects.create(project=other, name="theirs")

        resp = self.client.get(self.detail_url(policy))
        assert resp.status_code == 404

    def test_retrieve_update_delete(self):
        policy = RoutingPolicy.objects.create(
            project=self.project, name="orig", description="before"
        )

        resp = self.client.get(self.detail_url(policy))
        assert resp.status_code == 200, resp.content
        assert resp.data["name"] == "orig"

        resp = self.client.patch(
            self.detail_url(policy), {"description": "after"}, format="json"
        )
        assert resp.status_code == 200, resp.content
        policy.refresh_from_db()
        assert policy.description == "after"

        resp = self.client.delete(self.detail_url(policy))
        assert resp.status_code == 204
        assert not RoutingPolicy.objects.filter(pk=policy.id).exists()

    def test_deleting_project_cascades_to_policies(self):
        RoutingPolicy.objects.create(project=self.project, name="doomed")
        self.client.delete(f"/api/projects/{self.project.id}/")
        assert RoutingPolicy.objects.count() == 0
