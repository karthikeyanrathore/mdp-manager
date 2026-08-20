from rest_framework import serializers

from .models import RoutingPolicy


class RoutingPolicySerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = RoutingPolicy
        fields = ["id", "project", "name", "description", "created_at"]
        read_only_fields = ["id", "project", "created_at"]

    def validate_name(self, value):
        # `project` comes from the URL rather than the body, so it is not a
        # writable field and DRF cannot build the (project, name) uniqueness
        # check itself. Without this the DB constraint would surface as a 500.
        policies = RoutingPolicy.objects.filter(
            project=self.context["view"].get_project(), name=value
        )
        if self.instance is not None:
            policies = policies.exclude(pk=self.instance.pk)
        if policies.exists():
            raise serializers.ValidationError(
                "A routing policy with this name already exists in this project."
            )
        return value


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutingPolicy
        fields = ["name", "description"]