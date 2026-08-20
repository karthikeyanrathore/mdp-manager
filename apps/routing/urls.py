from django.urls import path

from .views import RoutingPolicyViewSet

# DRF routers don't do nesting, so the two nested routes are wired by hand.
policy_list = RoutingPolicyViewSet.as_view({"get": "list", "post": "create"})
policy_detail = RoutingPolicyViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

urlpatterns = [
    path(
        "projects/<uuid:project_pk>/routing-policies/",
        policy_list,
        name="routing-policy-list",
    ),
    path(
        "projects/<uuid:project_pk>/routing-policies/<uuid:pk>/",
        policy_detail,
        name="routing-policy-detail",
    ),
]
