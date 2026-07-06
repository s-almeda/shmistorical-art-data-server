#!/bin/bash
#
# Build the art data server image. The tag matches docker_run.sh's default
# (shmistorical-art-data-server:local), so the two scripts pair up:
#
#   ./docker_build.sh
#   IMAGE=shmistorical-art-data-server:local LOCALDB_PATH=/root/LOCALDB \
#     GENERATED_MAPS=/root/generated_maps ./docker_run.sh
#
# NOTE: templates/ and static/ are COPYd into the image at build time, so a
# `git pull` + `docker restart` alone will NOT pick up code changes — you must
# rebuild (this script) and re-run docker_run.sh.
#
# Override the tag via env var:  IMAGE=myimage:tag ./docker_build.sh
set -euo pipefail

IMAGE="${IMAGE:-shmistorical-art-data-server:local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Build for the server's architecture (linux/amd64). On Apple Silicon this builds
# an emulated amd64 image, which is required because sqlite-vec's native vec0.so is
# x86_64 — an arm64 image fails at runtime with "wrong ELF class: ELFCLASS32". On an
# amd64 host this is a no-op. Override with PLATFORM=... ( PLATFORM="" = native ).
if [ -z "${PLATFORM:-}" ]; then
  case "$(uname -m)" in
    arm64|aarch64) PLATFORM="linux/amd64" ;;
    *)             PLATFORM="" ;;
  esac
fi

echo "Building image: $IMAGE  (platform: ${PLATFORM:-native})"
DOCKER_BUILDKIT=1 docker build ${PLATFORM:+--platform $PLATFORM} -t "$IMAGE" "$SCRIPT_DIR"

echo "✅ Built '$IMAGE'. Now run it, e.g.:"
echo "   IMAGE=$IMAGE LOCALDB_PATH=/root/LOCALDB GENERATED_MAPS=/root/generated_maps ./docker_run.sh"
