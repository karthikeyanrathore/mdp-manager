# mdp-manager

Manager serves as a routing manager for routing  messages aka "markdown" to respective policies.
It also serves as embedding manager to embed text which later can be used for semantic search.

model used: katanemo/Arch-Router-1.5B
model size: 2.9GB

read more about Arch Router in paper: https://arxiv.org/abs/2506.16655

## Setup

```bash
# 1. Infra (Postgres w/ pgvector + Redis)
docker-compose up -d

# 2. Python deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Config + DB
cp .env.example .env
python manage.py migrate

# Terminal A — API
python manage.py runserver

# Terminal B — Celery worker
celery -A config worker -l info
```


## Uni Message example

TBD