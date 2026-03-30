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

# Safe chezmoi apply: ensures 1Password token is loaded first
chezmoi_apply() {
    if [[ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
        echo "OP_SERVICE_ACCOUNT_TOKEN not set. Running load_op_token..."
        load_op_token
    fi
    if [[ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
        echo "ERROR: Could not load 1Password service account token from Keychain."
        echo "Store it with: security add-generic-password -a \$USER -s op-service-account-token -w YOUR_TOKEN"
        return 1
    fi
    chezmoi apply "$@"
}
