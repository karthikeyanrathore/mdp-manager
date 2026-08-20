# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Django REST Framework service that ingests markdown/text, embeds each document
with a **local** SentenceTransformer model (`all-MiniLM-L6-v2`, 384-dim), and
stores the vector in Postgres + `pgvector`, grouped per project. Embedding runs
**asynchronously** via Celery + Redis. Nothing reads the vectors back yet — the
search endpoint was removed and `ClusterView` is still a stub.

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
python manage.py test                                       # full suite
python manage.py test apps.routing                          # one app
python manage.py test apps.md.tests.MarkdownApiTests         # one class
python manage.py test apps.md.tests.MarkdownApiTests.test_upload_md_file  # one test
black .                    # format (CI runs `black --check --diff .`)
python manage.py makemigrations --check --dry-run      # CI drift guard
```

Optional compose services: `swagger-ui` (:8080, serves `spec/openapi.yaml`),
`pghero` (:8081, DB monitoring — needs `pg_stat_statements`), `db-backup` (daily
`pg_dump`). Backup/restore runbook: `docs/backup.md`; scripts in `scripts/`.

## Architecture

**App layout** — all Django apps live under `apps/` (a plain package with an
`__init__.py`); there is nothing importable at the repo root. Apps are listed in
`INSTALLED_APPS` by dotted path and their `AppConfig.name` must match. Django
derives the **label** from the last component, so the labels are `core` / `md` /
`routing`, and table names follow (`core_project`, `md_markdown`,
`routing_routingpolicy`). Reference apps by full dotted path everywhere (URL
`include()`s, `@patch` targets in tests).

- `apps/core/` — `Project`, the umbrella both other apps hang off. Owns
  `/api/projects/`. Depends on nothing.
- `apps/md/` — markdown ingest + embedding (below).
- `apps/routing/` — `RoutingPolicy` CRUD, nested under a project. A plain
  name/description resource; no routing behavior is attached to it yet.

`md` and `routing` both point at `core.Project` via the **string** reference
`"core.Project"` rather than importing the model. Dependency direction is
`core` ← `routing` ← `md`: `md/views.py` imports `RoutingPolicy` and its
serializer for the markdown→policies endpoint below. Keep it one-way — `routing`
must not import from `md`, and `core` must not import from either.

**Async ingest pipeline** — the request never blocks on embedding:

1. `POST /api/markdowns/` (JSON) or `/api/markdowns/upload/` (multipart `.md`) →
   `MarkdownViewSet` (`apps/md/views.py`) validates, creates a `Markdown`
   (`status=PENDING`), enqueues `embed_markdown.delay(id)`, returns **202**.
2. Celery task `embed_markdown` (`apps/md/tasks.py`): `PROCESSING` →
   `embed_texts()` (`apps/md/embedder.py`) over the full text → saves
   `Markdown.embedding` → `DONE` (or `FAILED` + retry). Clients poll
   `GET /api/markdowns/{id}/` for status.

**Data model**: `Project` (`apps/core/models.py`) 1—* `Markdown`
(`apps/md/models.py`) and 1—* `RoutingPolicy` (`apps/routing/models.py`); both
cascade on project delete. `Markdown.embedding` is a nullable `pgvector`
`VectorField(384)` — one vector per document, `NULL` until the task completes.
Ingest is scoped by project and requires a `project`.

**Markdown → policy**: `GET /api/markdowns/{id}/routing-policy/` (an `@action` on
`MarkdownViewSet`) resolves the markdown's project and returns **one** policy —
a single object, not a list. There is no markdown→policy FK, so which of the
project's policies applies is decided by `select_policy`
(`apps/routing/selection.py`). That function is the only place the rule lives;
its current body is a **placeholder** (newest policy wins) awaiting the real
criteria. 404 if the markdown is unknown or its project has no policies.

**Routing policies are nested** under a project
(`/api/projects/{project_pk}/routing-policies/`). DRF routers don't nest, so
`apps/routing/urls.py` wires the two routes by hand with `.as_view({...})`.
`project` comes from the URL, not the body, which means it is *not* a writable
serializer field — so DRF cannot auto-build the `unique_together(project, name)`
check. `RoutingPolicySerializer.validate_name` does it explicitly; without that
the DB constraint surfaces as a 500 instead of a 400.

**Embedding model loading** (`apps/md/embedder.py`): `get_model()` is
`@lru_cache`d so the ~90 MB model loads once per process; `sentence_transformers`
is imported *inside* the function, never at module top level.

**Config** (`config/`): settings are env-driven via `django-environ`
(`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `DEBUG`). Celery app is
`config/celery.py` (Redis broker/result backend). Django admin is enabled at
`/admin/` (create access via `python manage.py createsuperuser`).

## Gotchas

- **Tests never load PyTorch.** `embed_texts` is patched at the
  `apps.md.tasks` boundary and tasks run eagerly
  (`CELERY_TASK_ALWAYS_EAGER=True` via `override_settings`). When adding tests that
  ingest, mock `embed_texts` the same way — do not call the real model.
- **API tests need Postgres + pgvector** (the migrations run `CREATE EXTENSION
  vector`). Point the test DB at the pgvector container.
- **Admin CSS 404s when `DEBUG=False`** — no static serving is configured
  (no WhiteNoise / `collectstatic`). Use `DEBUG=True` or `runserver --insecure`
  locally.
- **Embedding dim (384) is pinned** to `all-MiniLM-L6-v2`. Changing
  `EMBEDDING_MODEL_NAME` requires a new migration for the vector column + re-embed.
- **Migrations have a merge node** (`md/0003_merge_...` reconciles `0002_project`
  and `0002_remove_chunk_chunk_emb_hnsw`). Preserve the merge when adding new
  migrations; `md/0004_markdown_embedding_delete_chunk` builds on it.
- **`Project` was moved out of `md` into `core`** by `core/0001_initial` +
  `md/0005_move_project_to_core`. Those are `SeparateDatabaseAndState`: `core/0001`
  physically renames `md_project` → `core_project` and *claims* the model in
  state, `md/0005` drops it from `md`'s state with no DDL. Don't "tidy" them into
  ordinary `CreateModel`/`DeleteModel` operations — that would drop and recreate
  the table, losing every project row.
- **Renaming an app is not just a directory move.** The label is what
  `django_migrations.app`, `django_content_type.app_label` and the table prefix
  are keyed on, so an existing database needs those rewritten by hand *before*
  `migrate` runs; it cannot be done from inside the renamed app's migrations.
  Fresh databases are fine. (The `embeddings` → `md` rename predates this file's
  current state; only fresh DBs are supported for it.)
- **No chunking.** Each markdown is one vector over its full text, and the model
  truncates at 256 word-pieces — only the opening of a long document contributes
  to its embedding. There is no HNSW index (removed in `0002_remove_chunk_...`).
- **Nothing consumes the embeddings.** `POST /api/search/` was removed, so the
  pipeline is currently write-only: `Markdown.embedding` is populated and never
  read. `pgvector`, `CosineDistance` and the vector column are all still in place
  for whatever reads them next.
- **Markdowns ingested before the chunking removal have `status=DONE` but
  `embedding IS NULL`.** They need re-enqueueing through `embed_markdown` if a
  future reader expects every `DONE` row to have a vector.
- `ClusterView` (`POST /api/cluster/`) is an intentional `pass` stub — not
  implemented.
