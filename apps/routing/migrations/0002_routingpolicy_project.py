import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("routing", "0001_initial"),
    ]

    operations = [
        # Added non-nullable with no default: the table is new and empty.
        migrations.AddField(
            model_name="routingpolicy",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="routing_policies",
                to="core.project",
            ),
        ),
        # Names are now unique per project rather than globally.
        migrations.AlterField(
            model_name="routingpolicy",
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterUniqueTogether(
            name="routingpolicy",
            unique_together={("project", "name")},
        ),
    ]
