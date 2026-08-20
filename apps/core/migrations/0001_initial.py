"""Move ``Project`` from the ``md`` app into ``core``.

The table already exists (created by ``md.0002_project``), so this does not
create it — it renames ``md_project`` to ``core_project`` at the database level
while telling Django's migration state that ``core.Project`` now owns it.
``md.0005_move_project_to_core`` then drops the model from the ``md`` state
without touching the table.

Rows, the primary key, and the ``md_markdown`` foreign key all survive: Postgres
repoints FK constraints automatically when a table is renamed.
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("md", "0004_markdown_embedding_delete_chunk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE md_project RENAME TO core_project;",
                    reverse_sql="ALTER TABLE core_project RENAME TO md_project;",
                ),
            ],
            state_operations=[
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
            ],
        ),
    ]
