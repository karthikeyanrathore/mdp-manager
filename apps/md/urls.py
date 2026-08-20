from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClusterView, MarkdownViewSet

router = DefaultRouter()
router.register("markdowns", MarkdownViewSet, basename="markdown")

urlpatterns = [
    path("", include(router.urls)),
    path("cluster/", ClusterView.as_view(), name="cluster"),
]
