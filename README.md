# shmistorical-art-data-server

A Flask data/ML server for an art "knowledgebase" — vector similarity search plus a
2D map-generation pipeline. It's the backend behind `data.snailbunny.site` and powers
two front ends (an art canvas app and a map explorer).

## What it does

- **Similarity search** over an art knowledgebase using precomputed embeddings stored
  in SQLite via [`sqlite-vec`](https://github.com/asg017/sqlite-vec):
  - MiniLM (`sentence-transformers`) for text
  - ResNet50 (`torchvision`) for images
  - CLIP for multimodal "baseline" search
  Only the *incoming query* is embedded at request time; the database embeddings are
  precomputed.
- **Map generation** — projects embeddings to 2D (UMAP) and builds Voronoi region maps
  (including a hierarchical variant), served synchronously or via an async job queue.
- **Comics** browse API.

## Endpoints (overview)

- **Similarity:** `POST /keyword_check`, `POST /lookup_text`, `POST /image`, `POST /lookup_entry`
- **Direct reads:** `GET /text/<id>`, `GET /artwork/<id>`, `POST /database_request`
- **Maps:** `GET /generate_initial_map`, `GET /generate_voronoi_map`,
  `GET /generate_hierarchical_voronoi_map`, `POST /merge_voronoi_regions`,
  async `POST /submit_map_job` → `GET /job_status/<id>` → `GET /get_result/<key>`,
  `GET /demo_maps`

See [docs/MAP_API.md](docs/MAP_API.md) for map request/response shapes.

## Architecture

Gunicorn serves the Flask app (`app/index.py` + blueprints under `app/templates/`,
helpers under `app/helper_functions/`). A background worker (`app/jobs/worker.py`) runs
long-running map jobs, with the queue and results in a local SQLite (`jobs/jobs.db`).
Both processes start from `app/bootstrap.sh`.

## Data is not in this repo

The databases and images are large and licensing-sensitive, so they are **mounted at
runtime**, never committed:

- `/app/LOCALDB` — `knowledgebase.db` (+ `images/`, `comics.db`)
- `/app/generated_maps` — the canonical + demo maps that get served, and the job cache

## Quickstart (Docker)

```bash
docker build -t shmistorical-art-data-server:local .

# point these at your mounted data, then run:
LOCALDB_PATH=/path/to/LOCALDB \
GENERATED_MAPS=/path/to/generated_maps \
./docker_run.sh
# serves on http://localhost:8080  (models download + cache on first run)
```

`docker_run.sh` mounts the data, the model caches, sets `--restart unless-stopped`,
and replaces any existing container.

## Configuration (env vars)

| var | purpose |
|-----|---------|
| `FINAL_SQL_ADMIN_PASSWORD` | gates the admin SQL endpoints (unset → disabled) |
| `STAGING_ADMIN_PASSWORD`   | gates the data-cleaner UI (unset → disabled, fail closed) |
| `RUNNING_IN_DOCKER`        | set to `true` inside the container |

See [.env.example](.env.example).

## License

MIT — see [LICENSE](LICENSE).
