#!/usr/bin/env zsh
# Install git pre-push hook that runs the full QA gate.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: not inside a git repository" >&2
  exit 1
}

HOOK="${ROOT}/.git/hooks/pre-push"
mkdir -p "$(dirname "${HOOK}")"

cat >"${HOOK}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec task qa:prepush
EOF

chmod +x "${HOOK}"
echo "Installed ${HOOK} → task qa:prepush"
