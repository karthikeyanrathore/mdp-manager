from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MarkdownViewSet, SearchView

router = DefaultRouter()
router.register("markdowns", MarkdownViewSet, basename="markdown")

urlpatterns = [
    path("", include(router.urls)),
    path("search/", SearchView.as_view(), name="search"),
]
