# LOCALDB — local data for the art data server

The server reads its databases and images from this folder (see
[`app/config.py`](../config.py)):

```
LOCALDB/
├── knowledgebase.db     art:    text_entries, image_entries          ← DB_PATH
├── comics.db            comics: text_entries, book_entries, image_entries
├── poetry.db            poetry: text_entries, book_entries, line_entries
└── images/              artwork + comic-page image files             ← IMAGES_PATH
```

The **real** databases and images are large and licensing-sensitive, so they are
**not** committed to git (they're mounted at runtime on the live server). This
folder instead ships the material needed to rebuild a small, *browsable* local
copy for development and transparency:

```
JSONs/                   sample exports (50–100 rows per table) from the live browser
build_scripts/           the scrapers/builders used to assemble the real corpus
                         (kept for transparency — not needed to run locally)
convert_json_to_db.py    turns JSONs/ into the .db files + images/ above
```

## Rebuild the databases yourself

You don't need the private data to get a working local instance — you can
regenerate a sample from the public browser:

1. Visit **https://data.snailbunny.site/**
2. For each dataset (art / comics / poetry) and each table, click
   **"Download as JSON"**.
3. Drop the files into [`JSONs/`](JSONs/) using these names:
   ```
   art_text_entries.json      art_image_entries.json
   comics_text_entries.json   comics_book_entries.json   comics_image_entries.json
   poetry_text_entries.json   poetry_book_entries.json   poetry_line_entries.json
   ```
   (A sample set is already checked in, so you can skip straight to step 4.)
4. Run the converter (stdlib only — nothing to `pip install`):
   ```bash
   cd app/LOCALDB
   python convert_json_to_db.py            # builds all three DBs + downloads images
   python convert_json_to_db.py --no-images   # rows only, no network
   python convert_json_to_db.py --datasets art --limit 20   # quick subset
   ```

That writes `knowledgebase.db`, `comics.db`, `poetry.db`, and populates
`images/` right here in `LOCALDB/`, which is exactly where the app looks when run
locally (non-Docker).

### What this does and doesn't rebuild

- ✅ **Browsable row tables** — enough for the database browser at `/` and the
  direct read/browse API routes.
- ❌ **Embeddings (vec0 tables)** — similarity search and the map generator need
  precomputed image/text/CLIP vectors. Regenerating those means running the
  models via the `build_scripts/` (`update_embeddings.py`, etc.). The converter
  does **not** produce them, so semantic search / maps won't work on a rebuilt
  local copy — browsing will.

## About `build_scripts/`

These are the scrapers and builders (BeautifulSoup / Playwright / API pulls) that
assembled the original corpus. They're included **for transparency**, not because
you need them to run locally, and they expect private inputs/credentials (e.g.
`XAPP_TOKEN` for the Artsy API) that aren't provided here.
