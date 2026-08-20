from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from apps.core.models import Project

from .models import RoutingPolicy
from .serializers import RoutingPolicySerializer


class RoutingPolicyViewSet(viewsets.ModelViewSet):
    """CRUD for a project's routing policies.

    Nested under a project, so `project` is taken from the URL rather than the
    request body. An unknown project id is a 404 rather than an empty list.
    """

    serializer_class = RoutingPolicySerializer

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["project_pk"])

    def get_queryset(self):
        return RoutingPolicy.objects.filter(project=self.get_project())

    def perform_create(self, serializer):
        serializer.save(project=self.get_project())
