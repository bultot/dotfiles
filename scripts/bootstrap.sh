#!/usr/bin/env bash
set -euo pipefail

# bootstrap.sh - Dev OS environment setup
# Idempotent: safe to run multiple times
# Usage: curl -fsSL https://raw.githubusercontent.com/bultot/dotfiles/main/scripts/bootstrap.sh | bash
# Or:    ./scripts/bootstrap.sh

DOTFILES_DIR="$HOME/.local/share/chezmoi"

info() { printf "\033[0;34m[info]\033[0m %s\n" "$1"; }
warn() { printf "\033[0;33m[warn]\033[0m %s\n" "$1"; }
error() { printf "\033[0;31m[error]\033[0m %s\n" "$1"; exit 1; }
ok() { printf "\033[0;32m[ok]\033[0m %s\n" "$1"; }

# --- Xcode Command Line Tools ---
if ! xcode-select -p &>/dev/null; then
    info "Installing Xcode Command Line Tools..."
    xcode-select --install
    info "Waiting for Xcode CLT installation. Re-run this script when done."
    exit 0
else
    ok "Xcode Command Line Tools installed"
fi

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    ok "Homebrew installed"
fi

# --- chezmoi ---
if ! command -v chezmoi &>/dev/null; then
    info "Installing chezmoi..."
    brew install chezmoi
else
    ok "chezmoi installed"
fi

# --- Initialize dotfiles with chezmoi ---
if [[ ! -d "$DOTFILES_DIR/.git" ]]; then
    info "First run: cloning dotfiles and applying with chezmoi..."
    info "chezmoi will prompt for configuration values (name, email, machine type)"
    chezmoi init --apply bultot/dotfiles
else
    ok "Dotfiles repo exists at $DOTFILES_DIR"
    info "Applying dotfiles with chezmoi..."
    chezmoi apply
fi

ok "chezmoi applied"

# --- Brewfile ---
if [[ -f "$DOTFILES_DIR/Brewfile" ]]; then
    info "Installing Homebrew packages from Brewfile..."
    brew bundle install --file="$DOTFILES_DIR/Brewfile" --no-lock
else
    warn "No Brewfile found at $DOTFILES_DIR/Brewfile, skipping brew bundle"
fi

# --- Verify ---
info "Verifying installation..."
MISSING=()
for cmd in starship zoxide fzf bat eza rg direnv tmux chezmoi gh; do
    if ! command -v "$cmd" &>/dev/null; then
        MISSING+=("$cmd")
    fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
    warn "Missing commands: ${MISSING[*]}"
    warn "Try: brew bundle install --file=$DOTFILES_DIR/Brewfile"
else
    ok "All CLI tools verified"
fi

echo ""
ok "Bootstrap complete. Open a new terminal to load the shell config."
