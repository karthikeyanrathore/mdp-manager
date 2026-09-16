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

    def create(self, validated_data):
        # The same text twice in one project is a re-ingest of a document the
        # project already has, so hand back the row that already holds it
        # instead of storing a second copy. Done here rather than with a DB
        # constraint: Postgres cannot put a unique index on a raw text column
        # (long documents exceed the btree row limit), so enforcing it in the
        # schema would mean a hash column plus deleting the duplicates already
        # stored.

        # Exact match query.
        existing = Markdown.objects.filter(
            project=validated_data["project"], text=validated_data["text"]
        ).first()
        if existing is not None:
            print("Ok, Md text aleardy in db.")
            return existing
        return super().create(validated_data)
