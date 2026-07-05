#!/usr/bin/env python3
"""
convert_json_to_db.py
=====================
Rebuild local SQLite databases (+ images) from the JSON exports in ``JSONs/`` so
that a fresh checkout of this repo has *browsable* data to run against.

Workflow (see LOCALDB/README.md for the full version):
    1. visit  https://data.snailbunny.site/
    2. for each dataset (art / comics / poetry) and each table, hit
       "Download as JSON"
    3. drop the files in  LOCALDB/JSONs/  using the names below
    4. run:  python convert_json_to_db.py

Expected files in JSONs/ (missing ones are simply skipped):
    art_text_entries.json      art_image_entries.json
    comics_text_entries.json   comics_book_entries.json   comics_image_entries.json
    poetry_text_entries.json   poetry_book_entries.json   poetry_line_entries.json

Produces (next to this script, i.e. inside LOCALDB/ where config.py looks):
    knowledgebase.db   art:    text_entries, image_entries
    comics.db          comics: text_entries, book_entries, image_entries
    poetry.db          poetry: text_entries, book_entries, line_entries
    images/            artwork + comic-page images (only with --images)

Only stdlib is used, so this runs without installing anything.

NOTE: this rebuilds the browsable row tables only. Similarity search and the map
generator additionally need embedding (vec0) tables, which require running the
models — see the build_scripts/ (update_embeddings.py, etc.). Those are NOT
produced here; browsing the data will work, semantic search will not.
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- table specs -----------------------------------------------------------
# Column lists mirror the CREATE TABLE statements in build_scripts/. Any extra
# keys found in the JSON but not listed here (e.g. comics image `ocr_text`) are
# appended automatically as TEXT columns, so no data is dropped.
DATASETS = {
    "art": {
        "db": "knowledgebase.db",
        "tables": {
            "text_entries": {
                "json": "art_text_entries.json", "pk": "entry_id",
                "columns": ["entry_id", "value", "images", "isArtist", "type",
                            "artist_aliases", "descriptions",
                            "relatedKeywordIds", "relatedKeywordStrings"],
                "int_cols": ["isArtist"],
            },
            "image_entries": {
                "json": "art_image_entries.json", "pk": "image_id", "has_images": True,
                "columns": ["image_id", "value", "artist_names", "image_urls",
                            "filename", "rights", "descriptions",
                            "relatedKeywordIds", "relatedKeywordStrings"],
                "int_cols": [],
            },
        },
    },
    "comics": {
        "db": "comics.db",
        "tables": {
            "text_entries": {
                "json": "comics_text_entries.json", "pk": "entry_id",
                "columns": ["entry_id", "value", "images", "isArtist", "type",
                            "artist_aliases", "descriptions",
                            "relatedKeywordIds", "relatedKeywordStrings"],
                "int_cols": ["isArtist"],
            },
            "book_entries": {
                "json": "comics_book_entries.json", "pk": "book_id",
                "columns": ["book_id", "value", "series_id", "issue_number",
                            "cover_date", "page_count", "pages", "cover_image_id",
                            "descriptions", "relatedKeywordIds", "relatedKeywordStrings"],
                "int_cols": ["issue_number", "page_count"],
            },
            "image_entries": {
                "json": "comics_image_entries.json", "pk": "image_id", "has_images": True,
                "columns": ["image_id", "value", "artist_names", "image_urls",
                            "filename", "rights", "descriptions",
                            "relatedKeywordIds", "relatedKeywordStrings",
                            "book_id", "page_number"],
                "int_cols": ["page_number"],
            },
        },
    },
    "poetry": {
        "db": "poetry.db",
        "tables": {
            "text_entries": {
                "json": "poetry_text_entries.json", "pk": "entry_id",
                "columns": ["entry_id", "value", "lines", "isArtist", "type",
                            "artist_aliases", "descriptions",
                            "relatedKeywordIds", "relatedKeywordStrings"],
                "int_cols": ["isArtist"],
            },
            "book_entries": {
                "json": "poetry_book_entries.json", "pk": "book_id",
                "columns": ["book_id", "value", "gid", "author_id", "line_count",
                            "lines", "descriptions",
                            "relatedKeywordIds", "relatedKeywordStrings"],
                "int_cols": ["line_count"],
            },
            "line_entries": {
                "json": "poetry_line_entries.json", "pk": "line_id",
                "columns": ["line_id", "value", "book_id", "line_number",
                            "descriptions", "relatedKeywordIds", "relatedKeywordStrings"],
                "int_cols": ["line_number"],
            },
        },
    },
}

# preference order when choosing which image resolution to download
IMAGE_URL_KEYS = ("small", "square", "thumb", "medium", "full",
                  "normalized", "large", "larger")


def load_rows(path):
    """Load a browser JSON export as a list of row dicts (tolerant of wrappers)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "rows", "entries", "results"):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError(f"{os.path.basename(path)}: could not find a list of rows")


def build_table(conn, name, spec, rows):
    """(Re)create `name` from `rows`, serializing nested values to JSON strings."""
    columns = list(spec["columns"])
    extra = sorted({k for r in rows for k in r} - set(columns))
    columns += extra  # keep any columns the export has beyond the base schema

    defs = []
    for col in columns:
        if col == spec["pk"]:
            defs.append(f'"{col}" TEXT PRIMARY KEY')
        elif col in spec.get("int_cols", []):
            defs.append(f'"{col}" INTEGER')
        else:
            defs.append(f'"{col}" TEXT')

    conn.execute(f'DROP TABLE IF EXISTS "{name}"')
    conn.execute(f'CREATE TABLE "{name}" ({", ".join(defs)})')

    placeholders = ", ".join("?" for _ in columns)
    col_list = ", ".join(f'"{c}"' for c in columns)
    sql = f'INSERT OR REPLACE INTO "{name}" ({col_list}) VALUES ({placeholders})'

    def cell(v):
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return v

    conn.executemany(sql, [[cell(r.get(c)) for c in columns] for r in rows])
    conn.commit()
    return columns, extra


def pick_image_url(urls):
    if not isinstance(urls, dict):
        return None
    for k in IMAGE_URL_KEYS:
        if isinstance(urls.get(k), str) and urls[k].startswith("http"):
            return urls[k]
    for v in urls.values():
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


def download_images(rows, images_dir, timeout=20):
    os.makedirs(images_dir, exist_ok=True)
    got = skipped = failed = 0
    for r in rows:
        fn = r.get("filename")
        if not fn:
            continue
        dest = os.path.join(images_dir, fn)
        if os.path.exists(dest):
            skipped += 1
            continue
        url = pick_image_url(r.get("image_urls"))
        if not url:
            failed += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "shm-localdb/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            with open(dest, "wb") as out:
                out.write(data)
            got += 1
        except Exception as exc:  # network is best-effort; keep going
            failed += 1
            print(f"      ! {fn}: {exc}")
    return got, skipped, failed


def main():
    ap = argparse.ArgumentParser(description="Rebuild local .db files from JSON exports.")
    ap.add_argument("--json-dir", default=os.path.join(SCRIPT_DIR, "JSONs"),
                    help="folder holding the *_entries.json exports (default: LOCALDB/JSONs)")
    ap.add_argument("--out-dir", default=SCRIPT_DIR,
                    help="where to write the .db files + images/ (default: LOCALDB/)")
    ap.add_argument("--datasets", default="art,comics,poetry",
                    help="comma-separated subset to build (default: all)")
    ap.add_argument("--no-images", action="store_true",
                    help="skip downloading images (rows only; much faster, no network)")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap rows per table (handy for a quick smoke test)")
    args = ap.parse_args()

    wanted = [d.strip() for d in args.datasets.split(",") if d.strip()]
    unknown = [d for d in wanted if d not in DATASETS]
    if unknown:
        sys.exit(f"Unknown dataset(s): {', '.join(unknown)}. Choose from {', '.join(DATASETS)}.")

    images_dir = os.path.join(args.out_dir, "images")

    for ds in wanted:
        cfg = DATASETS[ds]
        db_path = os.path.join(args.out_dir, cfg["db"])
        print(f"\n▶ {ds}  →  {cfg['db']}")
        conn = sqlite3.connect(db_path)
        try:
            for tname, spec in cfg["tables"].items():
                json_path = os.path.join(args.json_dir, spec["json"])
                if not os.path.exists(json_path):
                    print(f"   · {tname}: SKIP (missing {spec['json']})")
                    continue
                rows = load_rows(json_path)
                if args.limit:
                    rows = rows[: args.limit]
                _, extra = build_table(conn, tname, spec, rows)
                note = f"  (+extra cols: {', '.join(extra)})" if extra else ""
                print(f"   · {tname}: {len(rows)} rows{note}")

                if spec.get("has_images") and not args.no_images:
                    got, skipped, failed = download_images(rows, images_dir)
                    print(f"       images: {got} downloaded, {skipped} already present, {failed} failed")
        finally:
            conn.close()

    print(f"\n✅ Done. Databases in: {args.out_dir}")
    if not args.no_images:
        print(f"   Images in: {images_dir}")
    print("   (Similarity search / maps need embeddings — see build_scripts/.)")


if __name__ == "__main__":
    main()
