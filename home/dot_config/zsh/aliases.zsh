# File listing (eza replaces ls)
alias ls="eza --icons"
alias ll="eza -la --icons --git"
alias la="eza -a --icons"
alias lt="eza --tree --level=2 --icons"

# File viewing (bat replaces cat)
alias cat="bat --paging=never"
alias catp="bat --plain --paging=never"

# Git shortcuts
alias gs="git status"
alias gd="git diff"
alias gl="git log --oneline -20"
alias gco="git checkout"
alias gcb="git checkout -b"

# Navigation
alias ..="cd .."
alias ...="cd ../.."
alias ....="cd ../../.."

# Safety
alias rm="rm -i"
alias cp="cp -i"
alias mv="mv -i"

# Grep with color
alias grep="grep --color=auto"

# Docker shortcuts
alias dc="docker compose"
alias dps="docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

# Python
alias python=python3

# Claude Code with permissions skip
alias claude='command claude --dangerously-skip-permissions'

# 1Password: personal account shortcut (bypasses SA token for admin ops)
alias op-personal='OP_SERVICE_ACCOUNT_TOKEN="" op'

# MCP server health check
alias mcp-health="python3 ~/.local/share/chezmoi/scripts/mcp-health.py"

# Project health checks (on-demand, per D-14/D-15)
alias dev-health-node="bash ~/.local/share/chezmoi/scripts/health/node-health.sh"
alias dev-health-python="bash ~/.local/share/chezmoi/scripts/health/python-health.sh"
alias dev-health-infra="bash ~/.local/share/chezmoi/scripts/health/infra-health.sh"
