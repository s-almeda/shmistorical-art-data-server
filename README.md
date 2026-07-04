# shmistorical-art-data-server

A Flask data/ML server for an art "knowledgebase" — vector similarity search plus a
2D map-generation pipeline. It's the backend behind `data.snailbunny.site` and powers
two front ends (an art canvas app and a map explorer).

## About this knowledgebase

### Where does the data come from?

The historical artworks and art terms are the most substantial part of this corpus
(**_[N]_ artworks**, **_[N]_ text entries** including artist names and art / aesthetic /
cultural terms). We assembled it by combining public-domain art and metadata from
[WikiArt](https://www.wikiart.org/) with labels from
[The Artsy Genome Project](https://www.artsy.net/categories), an art-classification
system with ~1,000 terms for describing artworks. We have a text entry for every term
and artist, plus links that connect related terms, artists, and artworks across the
database. We also have image (ResNet50), text (MiniLM), and multimodal (CLIP)
embeddings for every entry.

The comics are public-domain comics from [Comic Book Plus](https://comicbookplus.com/).
This dataset is still being built and organized; planned work includes OCRing,
describing, and embedding every comic page.

The poetry dataset is Allison Parrish's
[Gutenberg Poetry Corpus](https://github.com/aparrish/gutenberg-poetry-corpus).

### How did you make this, and what can it do?

When there is no already-assembled dataset (or API) for a corpus of knowledge, I turn
to tools like BeautifulSoup and Playwright to scrape data from open sources. I've built
several tools that support the data curation / staging / organization process (ex: [data cleaner](https://data.snailbunny.site/data_cleaner), [staging review](https://data.snailbunny.site/staging_review/), [map check](https://data.snailbunny.site/map-check), etc) as well as API routes for querying this server and using the data in applications like
[Artographer](https://shmuh.co/artographer).

I'm working on making these tools, workflows, and APIs more available and accessible for
public use, which includes more documentation and public-facing design work, plus
creating policies and licenses about how this work should be used.

If you'd like to support this effort, please feel invited to
[reach out](https://shmuh.co/) or [send a tip](https://paypal.me/shmuh).

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
