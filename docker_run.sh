#!/bin/bash
#
# Run the art data server container.
#
# Host data is MOUNTED (never baked into the image):
#   LOCALDB_PATH    -> /app/LOCALDB        (knowledgebase.db + images [+ comics.db])
#   GENERATED_MAPS  -> /app/generated_maps (canonical + demo maps; also the job-result cache)
# Model weights cache to host dirs so they are not re-downloaded each run.
#
# Override any of these via env vars, e.g.:
#   IMAGE=shmistorical-art-data-server:local LOCALDB_PATH=/root/LOCALDB \
#   GENERATED_MAPS=/root/generated_maps ./docker_run.sh
#
set -euo pipefail

IMAGE="${IMAGE:-shmistorical-art-data-server:local}"
NAME="${NAME:-art-data-server}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Run the image at the server's architecture (linux/amd64). On Apple Silicon this
# runs emulated, which is required because sqlite-vec's native vec0.so is x86_64
# (an arm64 image fails with "wrong ELF class"). On an amd64 host this is a no-op.
# Override with PLATFORM=... ( PLATFORM="" forces native ).
if [ -z "${PLATFORM:-}" ]; then
  case "$(uname -m)" in
    arm64|aarch64) PLATFORM="linux/amd64" ;;
    *)             PLATFORM="" ;;
  esac
fi
LOCALDB_PATH="${LOCALDB_PATH:-$SCRIPT_DIR/app/LOCALDB}"
GENERATED_MAPS="${GENERATED_MAPS:-$SCRIPT_DIR/app/generated_maps}"
MODEL_CACHE="${MODEL_CACHE:-$HOME/model_cache}"
TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HOME/transformers_cache}"

# Guardrails: refuse to start with a missing/empty dataset.
if [ ! -f "$LOCALDB_PATH/knowledgebase.db" ]; then
  echo "❌ knowledgebase.db not found at $LOCALDB_PATH (set LOCALDB_PATH)."
  exit 1
fi
if [ ! -d "$LOCALDB_PATH/images" ]; then
  echo "❌ images/ not found at $LOCALDB_PATH (set LOCALDB_PATH)."
  exit 1
fi
mkdir -p "$GENERATED_MAPS" "$MODEL_CACHE" "$TRANSFORMERS_CACHE"

echo "Image:          $IMAGE"
echo "Platform:       ${PLATFORM:-native}"
echo "LOCALDB_PATH:   $LOCALDB_PATH"
echo "GENERATED_MAPS: $GENERATED_MAPS"

# Replace any existing container (|| true so a missing container doesn't abort).
docker stop "$NAME" 2>/dev/null || true
docker rm "$NAME" 2>/dev/null || true

docker run -d --name "$NAME" --restart unless-stopped -p 8080:8080 \
  ${PLATFORM:+--platform $PLATFORM} \
  -v "$LOCALDB_PATH:/app/LOCALDB" \
  -v "$GENERATED_MAPS:/app/generated_maps" \
  -v "$MODEL_CACHE:/root/.cache/torch/hub" \
  -v "$TRANSFORMERS_CACHE:/root/.cache/transformers" \
  -e RUNNING_IN_DOCKER=true \
  -e FINAL_SQL_ADMIN_PASSWORD="${FINAL_SQL_ADMIN_PASSWORD:-}" \
  "$IMAGE"

echo "✅ Started '$NAME'. Follow logs: docker logs -f $NAME"
docker ps --filter "name=$NAME"
