from rest_framework import serializers

from .models import Chunk, Markdown, Project


class ProjectSerializer(serializers.ModelSerializer):
    markdown_count = serializers.IntegerField(source="markdowns.count", read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "description", "markdown_count", "created_at"]
        read_only_fields = ["id", "markdown_count", "created_at"]


class ChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chunk
        fields = ["index", "text"]


class MarkdownSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    chunk_count = serializers.IntegerField(source="chunks.count", read_only=True)

    class Meta:
        model = Markdown
        fields = [
            "id",
            "project",
            "title",
            "text",
            "status",
            "error",
            "chunk_count",
            "created_at",
        ]
        read_only_fields = ["id", "status", "error", "chunk_count", "created_at"]


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField()
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=100)


class SearchResultSerializer(serializers.Serializer):
    markdown_id = serializers.UUIDField()
    index = serializers.IntegerField()
    text = serializers.CharField()
    distance = serializers.FloatField()
