from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClusterView, MarkdownViewSet, ProjectViewSet, SearchView

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("markdowns", MarkdownViewSet, basename="markdown")

urlpatterns = [
    path("", include(router.urls)),
    path("search/", SearchView.as_view(), name="search"),
    path("cluster/", ClusterView.as_view(), name="cluster"),
]
