from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routing.models import RoutingPolicy
from apps.routing.selection import select_policy
from apps.routing.serializers import RoutingPolicySerializer, PolicySerializer

from .models import Markdown
from .serializers import MarkdownSerializer
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

        serializer = self.get_serializer(
            data={
                "project": request.data.get("project"),
                "title": upload.name,
                "text": text,
            }
        )
        serializer.is_valid(raise_exception=True)
        markdown = serializer.save()
        embed_markdown.delay(str(markdown.id))
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"], url_path="routing-policy")
    def routing_policy(self, request, pk=None):
        """The single routing policy that applies to this markdown.

        There is no direct markdown → policy link; policies are owned by the
        project. So this resolves markdown → project → policies and lets
        `select_policy` pick which one of them applies.
        """
        markdown = self.get_object()
        policies = RoutingPolicy.objects.filter(project=markdown.project_id)
        policy = select_policy(markdown.text, policies)
        if policy is None:
            raise NotFound("This markdown's project has no routing policies.")
        return Response(PolicySerializer(policy).data)


class ClusterView(APIView):
    def post(self, request):
        # TODO: cluster all stored markdown embeddings and return important topics
        pass
