from rest_framework import serializers

from apps.core.models import Project

from .models import Markdown


class MarkdownSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = Markdown
        fields = [
            "id",
            "project",
            "title",
            "text",
            "status",
            "error",
            "created_at",
        ]
        read_only_fields = ["id", "status", "error", "created_at"]
