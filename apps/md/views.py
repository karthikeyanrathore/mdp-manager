from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.routing.models import RoutingPolicy
from apps.routing.selection import select_policy
from apps.routing.serializers import RoutingPolicySerializer, PolicySerializer

from .models import Markdown, PolicySelection
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
        skip_embed = bool(request.query_params.get("skip_embed", 0))
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        markdown = serializer.save()
        print("check", skip_embed)
        if skip_embed:
            print("Ok, skipping embedding.")
            markdown = Markdown.objects.get(pk=markdown.id)
            markdown.status = Markdown.Status.DONE
            markdown.error = ""
            markdown.save(update_fields=["status", "error"])
        else:
            print("Ok, embed model initiated")
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

        The answer is cached in `PolicySelection` — one row per markdown — so
        the router only runs the first time it is asked about a markdown.
        """
        markdown = self.get_object()
        print(f"markdown:{markdown.id}")
        selection = PolicySelection.objects.filter(markdown=markdown).first()
        print(f"selection:{selection}")
        if selection is None:
            selection = self._select_and_store(markdown)
        if selection.policy is None:
            raise NotFound(selection.error)
        return Response(PolicySerializer(selection.policy).data)

    def _select_and_store(self, markdown):
        """Run the router once and record what it decided.

        Failures are stored too (``policy=None``), so an unroutable markdown
        does not pay for inference again on the next request.
        """
        policies = RoutingPolicy.objects.filter(project=markdown.project_id)
        try:
            policy = select_policy(markdown.text, policies)
        except NotFound as exc:
            policy, error = None, str(exc.detail)
        else:
            error = (
                ""
                if policy is not None
                else "This markdown's project has no routing policies."
            )
        return PolicySelection.objects.create(
            markdown=markdown, policy=policy, error=error
        )


class ClusterView(APIView):
    def post(self, request):
        # TODO: cluster all stored markdown embeddings and return important topics
        pass
