from django.db import migrations
from pgvector.django import VectorField


class Migration(migrations.Migration):

    dependencies = [
        ("md", "0003_merge_0002_project_0002_remove_chunk_chunk_emb_hnsw"),
    ]

    operations = [
        migrations.AddField(
            model_name="markdown",
            name="embedding",
            field=VectorField(dimensions=384, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="chunk",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="chunk",
            name="markdown",
        ),
        migrations.DeleteModel(
            name="Chunk",
        ),
    ]
