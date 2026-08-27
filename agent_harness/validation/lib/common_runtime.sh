#!/usr/bin/env bash

# Agent Harness validation shared helpers.
# Default mode is incremental: reuse stable tool/runtime dependencies.
# Use HARNESS_VALIDATION_MODE=clean for an isolated final/CI-style gate.

HARNESS_VALIDATION_MODE="${HARNESS_VALIDATION_MODE:-incremental}"
HARNESS_CACHE_ROOT="${HARNESS_CACHE_ROOT:-${XDG_CACHE_HOME:-$HOME/.cache}/agent-harness}"

run_with_timeout() {
  local seconds="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "${seconds}s" "$@"
  else
    "$@"
  fi
}

ensure_pnpm() {
  local pnpm_version="$1"
  local registry="$2"

  if command -v pnpm >/dev/null 2>&1; then
    echo "  pnpm: $(pnpm --version)" >&2
    return
  fi

  echo "  安装 pnpm@$pnpm_version" >&2
  npm install --global "pnpm@$pnpm_version" \
    --registry "$registry" \
    --no-audit \
    --no-fund >&2
}

write_dsh_pnpm_policy() {
  local host_dir="$1"
  cat > "$host_dir/pnpm-workspace.yaml" <<'EOF'
# DeepSeek Harness 0.1.0-rc.8 integration-only build-script allowlist.
# Any newly introduced build-script dependency remains blocked until reviewed.
allowBuilds:
  '@deepseek-ai/dsh-subprocess-local': true
  '@google/genai': true
  koffi: true
  node-pty: true
  protobufjs: true
EOF
}

ensure_dsh_runtime() {
  local dsh_version="$1"
  local pnpm_version="$2"
  local registry="$3"

  ensure_pnpm "$pnpm_version" "$registry"

  local runtime_key="dsh-${dsh_version}-node-$(node -p 'process.versions.node.split(`.`)[0]')"
  local host_dir="$HARNESS_CACHE_ROOT/runtime/$runtime_key"
  local dsh_bin="$host_dir/node_modules/.bin/dsh"

  if [[ "$HARNESS_VALIDATION_MODE" != "clean" && -x "$dsh_bin" ]]; then
    echo "  DeepSeek Harness runtime = REUSE ($host_dir)" >&2
    printf '%s\n' "$dsh_bin"
    return
  fi

  if [[ "$HARNESS_VALIDATION_MODE" == "clean" ]]; then
    rm -rf "$host_dir"
  fi

  mkdir -p "$host_dir"
  cd "$host_dir"
  if [[ ! -f package.json ]]; then
    npm init -y >/dev/null
  fi
  write_dsh_pnpm_policy "$host_dir"

  echo "  DeepSeek Harness runtime = INSTALL @deepseek-ai/dsh@$dsh_version" >&2
  pnpm add \
    --registry "$registry" \
    --reporter append-only \
    "@deepseek-ai/dsh@$dsh_version" >&2

  test -x "$dsh_bin"
  printf '%s\n' "$dsh_bin"
}

package_signature() {
  local package_dir="$1"
  (
    cd "$package_dir"
    {
      sha256sum package.json
      if [[ -f package-lock.json ]]; then sha256sum package-lock.json; fi
    } | sha256sum | awk '{print $1}'
  )
}

npm_install_if_needed() {
  local package_dir="$1"
  local registry="$2"
  local timeout_seconds="$3"
  shift 3

  local stamp="$package_dir/node_modules/.agent-harness-install-signature"
  local signature
  signature="$(package_signature "$package_dir")"

  if [[ "$HARNESS_VALIDATION_MODE" != "clean" && -f "$stamp" && "$(cat "$stamp")" == "$signature" ]]; then
    echo "  dependencies = REUSE ($package_dir)"
    return
  fi

  mkdir -p "$package_dir/node_modules"
  (
    cd "$package_dir"
    local status=0
    run_with_timeout "$timeout_seconds" npm install \
      --registry "$registry" \
      --no-audit \
      --no-fund \
      --fetch-retries 1 \
      --fetch-retry-mintimeout 2000 \
      --fetch-retry-maxtimeout 10000 \
      --fetch-timeout 60000 \
      --loglevel info \
      "$@" || status=$?
    if [[ "$status" -ne 0 ]]; then
      echo "npm install 失败或超时（exit=$status）" >&2
      exit "$status"
    fi
  )

  printf '%s\n' "$signature" > "$stamp"
}
