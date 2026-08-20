# Reminders

- **Use Ray (ray.io)** — the distributed-compute framework — for the **chunking**,
  **embedding**, and **vector search** stages, to parallelize/scale them. When
  implementing or refactoring `embeddings/chunking.py`, `embeddings/embedder.py`,
  or the search path in `embeddings/views.py`, plan for Ray-based parallelism
  rather than plain synchronous/Celery-only execution. (This is Ray, not raylib.)
