#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

IMAGE="malikovpro/v8std-mcp"
LOCAL_TAG="local"
PUSH=0
SMOKE=0
PIP_INDEX_URL="${V8STD_PIP_INDEX_URL:-https://pypi.org/simple}"
PLATFORMS=""

usage() {
    cat <<EOF
Сборка и публикация self-contained MCP-образа v8std.

Использование:
    scripts/build_mcp_image.sh [опции]

Опции:
    --image NAME        Имя образа (по умолчанию malikovpro/v8std-mcp)
    --tag TAG           Локальный тег (по умолчанию local)
    --pip-index URL     Индекс PyPI (по умолчанию https://pypi.org/simple)
    --platforms LIST    Платформы для локальной сборки (по умолчанию — архитектура хоста)
    --push              Мультиархитектурная сборка и push в Docker Hub:
                        NAME:latest, NAME:YYYY-MM-DD, NAME:sha-XXXXXXXXXXXX
    --smoke             После локальной сборки запустить контейнер и проверить
                        ответ MCP на http://127.0.0.1:8765/mcp

Примеры:
    scripts/build_mcp_image.sh --smoke
    scripts/build_mcp_image.sh --push
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --image) IMAGE="$2"; shift 2 ;;
        --tag) LOCAL_TAG="$2"; shift 2 ;;
        --pip-index) PIP_INDEX_URL="$2"; shift 2 ;;
        --platforms) PLATFORMS="$2"; shift 2 ;;
        --push) PUSH=1; shift ;;
        --smoke) SMOKE=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'неизвестная опция: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ "${PUSH}" -eq 1 ] && [ "${SMOKE}" -eq 1 ]; then
    printf -- '--smoke работает только с локальной сборкой (без --push)\n' >&2
    exit 2
fi

REVISION="$(git -C "${REPO_ROOT}" rev-parse HEAD)"
CREATED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DATE_TAG="$(date -u +%Y-%m-%d)"
SHA_TAG="sha-$(git -C "${REPO_ROOT}" rev-parse --short=12 HEAD)"
DOCKERFILE="docker-compose-mcp-only/docker/Dockerfile.mcp"

BUILDER=""
SMOKE_NAME=""

cleanup() {
    if [ -n "${BUILDER}" ]; then
        docker buildx rm -f "${BUILDER}" >/dev/null 2>&1 || true
    fi
    if [ -n "${SMOKE_NAME}" ]; then
        docker rm -f "${SMOKE_NAME}" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

BUILD_ARGS=(
    --build-arg "REVISION=${REVISION}"
    --build-arg "CREATED=${CREATED}"
    --build-arg "PIP_INDEX_URL=${PIP_INDEX_URL}"
)

cd "${REPO_ROOT}"

if [ "${PUSH}" -eq 1 ]; then
    BUILDER="v8std-mcp-builder-$$"
    docker buildx create --name "${BUILDER}" --driver docker-container --use >/dev/null
    docker buildx build \
        --file "${DOCKERFILE}" \
        --platform "linux/amd64,linux/arm64" \
        --tag "${IMAGE}:latest" \
        --tag "${IMAGE}:${DATE_TAG}" \
        --tag "${IMAGE}:${SHA_TAG}" \
        --push \
        "${BUILD_ARGS[@]}" \
        .
    printf 'запушено: %s:latest, %s:%s, %s:%s\n' "${IMAGE}" "${IMAGE}" "${DATE_TAG}" "${IMAGE}" "${SHA_TAG}"
else
    PLATFORM_ARGS=()
    if [ -n "${PLATFORMS}" ]; then
        PLATFORM_ARGS=(--platform "${PLATFORMS}")
    fi
    docker build \
        --file "${DOCKERFILE}" \
        "${PLATFORM_ARGS[@]}" \
        --tag "${IMAGE}:${LOCAL_TAG}" \
        "${BUILD_ARGS[@]}" \
        .
    printf 'собрано: %s:%s\n' "${IMAGE}" "${LOCAL_TAG}"
fi

if [ "${SMOKE}" -eq 1 ]; then
    SMOKE_NAME="v8std-mcp-smoke-$$"
    docker run -d --name "${SMOKE_NAME}" \
        -p 127.0.0.1:8765:8765 \
        "${IMAGE}:${LOCAL_TAG}" >/dev/null
    ok=0
    for _ in $(seq 1 30); do
        code="$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --max-time 2 http://127.0.0.1:8765/mcp || true)"
        if [ "${code}" != "000" ]; then
            ok=1
            printf 'smoke: MCP ответил HTTP %s на http://127.0.0.1:8765/mcp\n' "${code}"
            break
        fi
        sleep 1
    done
    if [ "${ok}" -ne 1 ]; then
        printf 'smoke: нет ответа на http://127.0.0.1:8765/mcp, логи контейнера:\n' >&2
        docker logs "${SMOKE_NAME}" >&2 || true
        exit 1
    fi
    docker rm -f "${SMOKE_NAME}" >/dev/null
    SMOKE_NAME=""
fi
