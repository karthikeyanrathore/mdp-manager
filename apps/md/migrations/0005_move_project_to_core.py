"""Drop ``Project`` from the ``md`` state after ``core.0001`` adopted it.

Both operations are state-only. The table was already renamed to ``core_project``
by ``core.0001_initial``, and ``md_markdown.project_id`` still points at the same
rows — Postgres followed the rename — so no DDL is needed here.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("md", "0004_markdown_embedding_delete_chunk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="markdown",
                    name="project",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="markdowns",
                        to="core.project",
                    ),
                ),
                migrations.DeleteModel(name="Project"),
            ],
        ),
    ]
