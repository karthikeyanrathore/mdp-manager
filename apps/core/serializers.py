from rest_framework import serializers

from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    markdown_count = serializers.IntegerField(source="markdowns.count", read_only=True)
    routing_policy_count = serializers.IntegerField(
        source="routing_policies.count", read_only=True
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "markdown_count",
            "routing_policy_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "markdown_count",
            "routing_policy_count",
            "created_at",
        ]
