#!/usr/bin/env bash
set -euo pipefail

# ANSI colors (only when stdout is a TTY)
if [ -t 1 ]; then
  GREEN='\033[32m'; RED='\033[31m'; RESET='\033[0m'
else
  GREEN=''; RED=''; RESET=''
fi

PROJECT_DIR="${1:?Usage: python-health.sh <project-path>}"
PROJECT_DIR="${PROJECT_DIR/#\~/$HOME}"
FAILED=0
TOTAL=0
PASSED=0

check() {
  local label="$1"; shift
  TOTAL=$((TOTAL + 1))
  if "$@" >/dev/null 2>&1; then
    printf "  ${GREEN}[PASS]${RESET} %s\n" "$label"
    PASSED=$((PASSED + 1))
  else
    printf "  ${RED}[FAIL]${RESET} %s\n" "$label"
    FAILED=1
  fi
}

echo "Python Project Health: $(basename "$PROJECT_DIR")"
echo "========================"

check "Directory exists"          test -d "$PROJECT_DIR"
check "pyproject.toml or reqs"    bash -c "test -f '$PROJECT_DIR/pyproject.toml' || test -f '$PROJECT_DIR/requirements.txt'"
check "Virtual env (.venv)"       test -d "$PROJECT_DIR/.venv"
check ".env or .env.local"        bash -c "test -f '$PROJECT_DIR/.env' || test -f '$PROJECT_DIR/.env.local' || ! test -f '$PROJECT_DIR/.env.example'"
check "Git repo"                  git -C "$PROJECT_DIR" rev-parse --git-dir

echo ""
echo "Result: $PASSED/$TOTAL passed"
exit $FAILED
