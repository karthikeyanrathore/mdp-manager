from pgvector.django import CosineDistance
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .embedder import embed_texts
from .models import Chunk, Markdown
from .serializers import (
    ChunkSerializer,
    MarkdownSerializer,
    SearchRequestSerializer,
    SearchResultSerializer,
)
from .tasks import embed_markdown


class MarkdownViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Markdown.objects.all()
    serializer_class = MarkdownSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        markdown = serializer.save()
        embed_markdown.delay(str(markdown.id))
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_202_ACCEPTED, headers=headers
        )

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": "No file was uploaded."})
        if not upload.name.lower().endswith(".md"):
            raise ValidationError({"file": "Only .md files are accepted."})
        try:
            text = upload.read().decode("utf-8")
        except UnicodeDecodeError:
            raise ValidationError({"file": "File must be UTF-8 encoded text."})

        markdown = Markdown.objects.create(title=upload.name, text=text)
        embed_markdown.delay(str(markdown.id))
        serializer = self.get_serializer(markdown)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"])
    def chunks(self, request, pk=None):
        markdown = self.get_object()
        queryset = markdown.chunks.all()
        page = self.paginate_queryset(queryset)
        serializer = ChunkSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class SearchView(APIView):
    def post(self, request):
        request_serializer = SearchRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        query = request_serializer.validated_data["query"]
        top_k = request_serializer.validated_data["top_k"]

        query_vector = embed_texts([query])[0]
        results = Chunk.objects.annotate(
            distance=CosineDistance("embedding", query_vector)
        ).order_by("distance")[:top_k]

        data = [
            {
                "markdown_id": chunk.markdown_id,
                "index": chunk.index,
                "text": chunk.text,
                "distance": chunk.distance,
            }
            for chunk in results
        ]
        return Response(SearchResultSerializer(data, many=True).data)
