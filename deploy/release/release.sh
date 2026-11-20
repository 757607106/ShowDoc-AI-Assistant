#!/usr/bin/env bash
set -euo pipefail

release_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$release_dir/../.."
umask 077
mkdir -p .runtime
exec 9>.runtime/release.lock
flock -n 9 || { echo '已有发版正在执行。' >&2; exit 1; }

if [[ -n $(git status --porcelain --untracked-files=no) ]]; then
    echo '发版工作区有未提交的变更，请先恢复为干净的检出。' >&2
    exit 1
fi
case "${1:-}" in
    '')
        upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}')
        for attempt in 1 2 3; do
            if GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=25 fetch; then
                break
            fi
            if [[ $attempt == 3 ]]; then
                exit 1
            fi
            sleep "$attempt"
        done
        git merge --ff-only "$upstream"
        if [[ "$release_dir" != "$PWD/deploy/release" && -x deploy/release/release.sh ]]; then
            exec 9>&-
            exec ./deploy/release/release.sh --local
        fi
        ;;
    --local) ;;
    *) echo '用法：release.sh [--local]' >&2; exit 2 ;;
esac

docker=(docker)
if ! docker info >/dev/null 2>&1; then
    docker=(sudo -n --preserve-env=RELEASE_REVISION,SANDBOX_CONFIG_REVISION,BUILDKIT_PROGRESS docker)
fi
if [[ -d .runtime/docker ]]; then
    docker+=(--config "$PWD/.runtime/docker")
fi
"${docker[@]}" info >/dev/null

config_dir=.runtime/production
if [[ ! -d $config_dir ]]; then
    if "${docker[@]}" volume inspect showdoc-ai-assistant_postgres >/dev/null 2>&1; then
        echo '数据库卷已存在，请先恢复 .runtime/production 中的配置。' >&2
        exit 1
    fi
    staging=$(mktemp -d .runtime/.production.XXXXXX)
    platform_password=$(openssl rand -hex 24)
    agent_password=$(openssl rand -hex 24)
    cat > "$staging/postgres.env" <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 32)
POSTGRES_PLATFORM_PASSWORD=$platform_password
POSTGRES_AGENT_PASSWORD=$agent_password
EOF
    cat > "$staging/app.env" <<EOF
SHOWDOC_HTTP_BIND=127.0.0.1
SHOWDOC_HTTP_PORT=18080
DATABASE_URL=postgresql://showdoc_platform:$platform_password@postgres:5432/showdoc_knowledge
AGENT_DATABASE_URL=postgresql://showdoc_agent:$agent_password@postgres:5432/showdoc_agent
FLASK_SECRET_KEY=$(openssl rand -hex 32)
CREDENTIAL_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')
SYSTEM_AES_KEY=$(openssl rand -hex 16)
PLATFORM_ADMIN_ACCOUNT=admin
PLATFORM_ADMIN_PASSWORD=$(openssl rand -hex 24)
EOF
    mv "$staging" "$config_dir"
fi

if [[ ! -f $config_dir/services.env ]]; then
    staging=$(mktemp "$config_dir/.services.XXXXXX")
    sandbox_password=$(openssl rand -hex 24)
    cat > "$staging" <<EOF
GOVERNANCE_DATA_DIR=/data
POSTGRES_ASYNC_PASSWORD=$(openssl rand -hex 24)
POSTGRES_SANDBOX_PASSWORD=$sandbox_password
OPENSANDBOX_STORE_POSTGRESQL_DSN=postgresql://opensandbox_control:$sandbox_password@postgres:5432/opensandbox_control
ASYNC_AGENT_RUNTIME_SIGNING_KEY=$(openssl rand -hex 32)
OPEN_SANDBOX_API_KEY=$(openssl rand -hex 32)
EOF
    mv "$staging" "$config_dir/services.env"
fi

# Publish sandbox execution ports only on the Docker bridge gateway.
bridge_ip=$("${docker[@]}" network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}')
[[ $bridge_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
staging=$(mktemp "$config_dir/.opensandbox.XXXXXX")
sed -e 's/^resolve_internal = true$/resolve_internal = false/' \
    -e "s/^publish_host = .*$/publish_host = \"$bridge_ip\"/" deploy/opensandbox.local.toml > "$staging"
if cmp -s "$staging" "$config_dir/opensandbox.toml"; then
    rm "$staging"
else
    mv "$staging" "$config_dir/opensandbox.toml"
fi
chmod 0644 "$config_dir/opensandbox.toml"

export RELEASE_REVISION SANDBOX_CONFIG_REVISION
RELEASE_REVISION=$(git rev-parse --short=12 HEAD)
SANDBOX_CONFIG_REVISION=$(sha256sum "$config_dir/opensandbox.toml" | cut -d ' ' -f 1)
compose=("${docker[@]}" compose --project-directory "$PWD" --env-file "$config_dir/app.env"
    --env-file "$config_dir/services.env" -f "$release_dir/compose.yml")
"${compose[@]}" config --quiet

builder=showdoc-ai-assistant
label=io.showdoc-ai-assistant.release=true
app_image="showdoc-ai-assistant-app:$RELEASE_REVISION"
web_image="showdoc-ai-assistant-web:$RELEASE_REVISION"
agent_image="showdoc-ai-assistant-agent-runtime:$RELEASE_REVISION"
build_started=$SECONDS
if ! "${docker[@]}" image inspect "$app_image" "$web_image" "$agent_image" >/dev/null 2>&1; then
    if ! "${docker[@]}" buildx history rm --help | grep -q -- '--all'; then
        echo '需要支持 buildx history rm 的 Docker Buildx。' >&2
        exit 1
    fi
    if ! "${docker[@]}" buildx inspect "$builder" >/dev/null 2>&1; then
        builder_args=()
        if [[ -f .runtime/buildkitd.toml ]]; then
            builder_args=(--buildkitd-config .runtime/buildkitd.toml)
        fi
        "${docker[@]}" buildx create --driver docker-container --name "$builder" "${builder_args[@]}"
    fi
    build=("${docker[@]}" buildx build --builder "$builder" --pull=false --load --label "$label")
    "${docker[@]}" image inspect "$app_image" >/dev/null 2>&1 ||
        "${build[@]}" -t "$app_image" -f "$release_dir/app.Dockerfile" .
    "${docker[@]}" image inspect "$web_image" >/dev/null 2>&1 ||
        "${build[@]}" -t "$web_image" --build-arg "VITE_FRONTEND_COMMIT=$RELEASE_REVISION" frontend
    if ! "${docker[@]}" image inspect "$agent_image" >/dev/null 2>&1; then
        git -c tar.umask=0022 archive HEAD agent governance common integrations deploy/async-agent |
            "${build[@]}" -t "$agent_image" -f deploy/async-agent/Dockerfile \
                --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ -
    fi
    did_build=1
else
    printf '复用 %s 的应用、前端和异步运行镜像。\n' "$RELEASE_REVISION"
fi

service_images=$("${compose[@]}" config --images)
sandbox_images=$(sed -nE 's/^(execd_image|image) = "([^"]+)".*$/\2/p' "$config_dir/opensandbox.toml")
while IFS= read -r image; do
    if [[ -n $image ]]; then
        "${docker[@]}" image inspect "$image" >/dev/null 2>&1 || "${docker[@]}" pull "$image"
    fi
done < <(printf '%s\n' "$service_images" "$sandbox_images" python:3.12-slim | sort -u)
"${compose[@]}" up -d --no-build --pull never --wait --wait-timeout 90 postgres
"${compose[@]}" exec -T postgres psql -X -q -v ON_ERROR_STOP=1 -U showdoc -d showdoc_knowledge \
    < "$release_dir/postgres.sql"
"${compose[@]}" run --rm --no-deps app python -m webapi.auth --bootstrap
"${compose[@]}" up -d --no-build --pull never --wait --wait-timeout 180

if "${docker[@]}" buildx inspect "$builder" >/dev/null 2>&1; then
    "${docker[@]}" buildx --builder "$builder" history rm --all
    if [[ ${did_build:-} ]]; then
        # Keep layers used by this release available for the next build.
        "${docker[@]}" buildx prune --builder "$builder" --force \
            --filter "until=$((SECONDS - build_started + 1))s"
    fi
fi
"${docker[@]}" image prune --all --force --filter "label=$label"
printf '发版成功：%s\n' "$RELEASE_REVISION"
