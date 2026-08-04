# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Django REST Framework service that ingests markdown/text, splits it into
overlapping chunks, embeds each chunk with a **local** SentenceTransformer model
(`all-MiniLM-L6-v2`, 384-dim), and stores the vectors in Postgres + `pgvector` for
per-project semantic search. Embedding runs **asynchronously** via Celery + Redis.

## Workflow

Whenever you produce a plan and then start implementing it, **first ask the user
whether to create a new branch for this feature or work in the current branch.**

- If they want a new branch, create it before writing any code and do all the work
  there — never commit the feature directly to `main` or `develop`. Name it
  `feat/<feature-name>` (kebab-case; git branch names cannot contain spaces or `:`,
  so use this form of the `feat: <feature>` convention):

  ```bash
  git switch -c feat/<feature-name>
  ```

- If they want to stay on the current branch, do the work there instead.

## Commands

Infra + app run separately (there is no app container in compose):

```bash
docker-compose up -d postgres redis      # required backing services
pip install -r requirements.txt
# ensure .env has DATABASE_URL, REDIS_URL, SECRET_KEY, DEBUG
python manage.py migrate
python manage.py runserver               # API on :8000
```

Celery worker — **on macOS you MUST use a non-forking pool** or the worker aborts
with `SIGABRT`/`WorkerLostError` (PyTorch is not fork-safe under macOS `fork()`):

```bash
celery -A config worker -l info --pool=solo        # macOS / dev
celery -A config worker -l info                     # Linux/Docker (prefork is fine)
```

Tests, lint, migrations:

```bash
python manage.py test                                  # full suite
python manage.py test embeddings.tests.ChunkTextTests  # one class
python manage.py test embeddings.tests.MarkdownApiTests.test_search_scoped_to_project  # one test
black .                    # format (CI runs `black --check --diff .`)
python manage.py makemigrations --check --dry-run      # CI drift guard
```

Optional compose services: `swagger-ui` (:8080, serves `spec/openapi.yaml`),
`pghero` (:8081, DB monitoring — needs `pg_stat_statements`), `db-backup` (daily
`pg_dump`). Backup/restore runbook: `docs/backup.md`; scripts in `scripts/`.

## Architecture

**Async ingest pipeline** — the request never blocks on embedding:

1. `POST /api/markdowns/` (JSON) or `/api/markdowns/upload/` (multipart `.md`) →
   `MarkdownViewSet` (`embeddings/views.py`) validates, creates a `Markdown`
   (`status=PENDING`), enqueues `embed_markdown.delay(id)`, returns **202**.
2. Celery task `embed_markdown` (`embeddings/tasks.py`): `PROCESSING` →
   `chunk_text()` (`embeddings/chunking.py`) → `embed_texts()`
   (`embeddings/embedder.py`) → `bulk_create` `Chunk` rows → `DONE` (or `FAILED`
   + retry). Clients poll `GET /api/markdowns/{id}/` for status.
3. `POST /api/search/` embeds the query and ranks chunks by `CosineDistance`.

**Data model** (`embeddings/models.py`): `Project` 1—* `Markdown` 1—* `Chunk`.
`Chunk.embedding` is a `pgvector` `VectorField(384)`. Everything is scoped by
project: ingest requires a `project`, and **search requires a `project`** and only
sees `Chunk.objects.filter(markdown__project=...)`.

**Embedding model loading** (`embeddings/embedder.py`): `get_model()` is
`@lru_cache`d so the ~90 MB model loads once per process; `sentence_transformers`
is imported *inside* the function, never at module top level.

**Config** (`config/`): settings are env-driven via `django-environ`
(`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `DEBUG`). Celery app is
`config/celery.py` (Redis broker/result backend). Django admin is enabled at
`/admin/` (create access via `python manage.py createsuperuser`).

## Gotchas

- **Tests never load PyTorch.** `embed_texts` is patched at the `embeddings.tasks`
  / `embeddings.views` boundaries and tasks run eagerly
  (`CELERY_TASK_ALWAYS_EAGER=True` via `override_settings`). When adding tests that
  ingest/search, mock `embed_texts` the same way — do not call the real model.
- **API tests need Postgres + pgvector** (the migrations run `CREATE EXTENSION
  vector` and build the HNSW index). Point the test DB at the pgvector container.
- **Admin CSS 404s when `DEBUG=False`** — no static serving is configured
  (no WhiteNoise / `collectstatic`). Use `DEBUG=True` or `runserver --insecure`
  locally.
- **Embedding dim (384) is pinned** to `all-MiniLM-L6-v2`. Changing
  `EMBEDDING_MODEL_NAME` requires a new migration for the vector column + re-embed.
- **Migrations have a merge node** (`0003_merge_...` reconciles `0002_project`
  and `0002_remove_chunk_chunk_emb_hnsw`). Preserve the merge when adding new
  migrations.
- `ClusterView` (`POST /api/cluster/`) is an intentional `pass` stub — not
  implemented.
