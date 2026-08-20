import uuid

import django.db.models.deletion
from django.db import migrations, models


def assign_default_project(apps, schema_editor):
    Project = apps.get_model("md", "Project")
    Markdown = apps.get_model("md", "Markdown")
    orphans = Markdown.objects.filter(project__isnull=True)
    if orphans.exists():
        default, _ = Project.objects.get_or_create(name="Default")
        orphans.update(project=default)


class Migration(migrations.Migration):
    dependencies = [
        ("md", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name="markdown",
            name="project",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="markdowns",
                to="md.project",
            ),
        ),
        migrations.RunPython(assign_default_project, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="markdown",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="markdowns",
                to="md.project",
            ),
        ),
    ]
