#!/bin/bash
set -e
echo "=== RASID Setup ==="
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    [ -f .env.example ] && cp .env.example .env && echo "Created .env" || { echo "ERROR: no .env found"; exit 1; }
fi

# ─── 1. Start DinD ────────────────────────────────────────────────────────
echo "[1/5] Starting Docker-in-Docker..."
docker compose up -d docker

echo -n "  Waiting for DinD daemon"
for i in $(seq 1 120); do
    DOCKER_CID=$(docker compose ps -q docker 2>/dev/null)
    if [ -n "$DOCKER_CID" ] && docker exec "$DOCKER_CID" docker info >/dev/null 2>&1; then
        echo " ready."
        break
    fi
    echo -n "."
    sleep 1
    if [ "$i" -eq 120 ]; then
        echo ""
        echo "ERROR: DinD not ready after 120s"
        docker compose logs docker --tail 20
        exit 1
    fi
done

# ─── 2. Pull tool images (with retries) ───────────────────────────────────
echo "[2/5] Pulling tool images..."
for image in \
    "instrumentisto/nmap:latest" \
    "projectdiscovery/httpx:latest" \
    "projectdiscovery/nuclei:latest" \
    "projectdiscovery/subfinder:latest" \
    "caffix/amass:latest" \
    "ilyaglow/masscan:latest"
do
    for attempt in 1 2 3; do
        echo "  ↓ $image (try $attempt/3)"
        if docker exec "$DOCKER_CID" docker pull "$image"; then
            break
        fi
        [ "$attempt" -lt 3 ] && sleep 5 || echo "  ⚠ giving up on $image"
    done
done

# ─── 3. Build custom images INSIDE DinD ───────────────────────────────────
# We copy the Dockerfile into the DinD container first, then run
# `docker build` from inside it. This is the only approach that works
# across all docker engine versions regardless of BuildKit settings.
build_in_dind() {
    local dockerfile="$1"
    local tag="$2"
    [ -f "$dockerfile" ] || { echo "  ⚠ $dockerfile not found"; return 0; }
    echo "  🔨 building $tag"
    local tmpdir="/tmp/rasid-build-$(date +%s)"
    docker exec "$DOCKER_CID" mkdir -p "$tmpdir"
    docker cp "$dockerfile" "$DOCKER_CID:$tmpdir/Dockerfile"
    docker exec "$DOCKER_CID" docker build -t "$tag" "$tmpdir"
    docker exec "$DOCKER_CID" rm -rf "$tmpdir"
    echo "  ✓ $tag"
}

echo "[3/5] Building custom images..."
build_in_dind "Dockerfile.nuclei"  "rasid/nuclei:latest"
build_in_dind "Dockerfile.massdns" "rasid/massdns:latest"

grep -q "^TOOL_NUCLEI_IMAGE="  .env && sed -i 's|^TOOL_NUCLEI_IMAGE=.*|TOOL_NUCLEI_IMAGE=rasid/nuclei:latest|'  .env || echo "TOOL_NUCLEI_IMAGE=rasid/nuclei:latest"  >> .env
grep -q "^TOOL_MASSDNS_IMAGE=" .env && sed -i 's|^TOOL_MASSDNS_IMAGE=.*|TOOL_MASSDNS_IMAGE=rasid/massdns:latest|' .env || echo "TOOL_MASSDNS_IMAGE=rasid/massdns:latest" >> .env

# ─── 4. Start full stack ──────────────────────────────────────────────────
echo "[4/5] Starting api, worker, db, redis..."
docker compose up --build -d
echo "  Waiting 20s for Postgres..."
sleep 20

# ─── 5. Migrations ────────────────────────────────────────────────────────
echo "[5/5] Running migrations..."
docker compose exec -T api alembic upgrade head && echo "  ✓ done" || echo "  ⚠ failed — run: docker compose exec api alembic upgrade head"

echo ""
echo "=========================================="
echo "✓ RASID is up."
echo "  API:      http://localhost:8000/health"
echo "  Frontend: cd ../frontend && npm install && npm run dev"
echo "  Then:     http://localhost:5173"
echo "First registered user = Admin."
echo "=========================================="
