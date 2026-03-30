# Create directory and cd into it
mkcd() {
    mkdir -p "$1" && cd "$1"
}

# Quick project jump (uses zoxide under the hood)
proj() {
    cd ~/projects/"${1:-}"
}

# Git commit with conventional format
gc() {
    git commit -m "$*"
}

# Lazy-load GitHub token (avoids prompt at shell start)
github_token() {
    if [[ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]]; then
        export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token 2>/dev/null)
    fi
    echo "$GITHUB_PERSONAL_ACCESS_TOKEN"
}

# 1Password: sa-claude-code service account token (Keychain + session cache)
load_op_token() {
    local _op_cache="/tmp/.op-sa-token-$(id -u)"
    if [[ -f "$_op_cache" && -O "$_op_cache" ]]; then
        export OP_SERVICE_ACCOUNT_TOKEN="$(<"$_op_cache")"
    else
        local _token
        _token="$(security find-generic-password -a "$USER" -s "op-service-account-token" -w 2>/dev/null)"
        if [[ -n "$_token" ]]; then
            export OP_SERVICE_ACCOUNT_TOKEN="$_token"
            printf '%s' "$_token" > "$_op_cache"
            chmod 600 "$_op_cache"
        fi
    fi
}
load_op_token
