# Dotfiles

Robin's dev environment managed by chezmoi.

## Quick Start

```sh
# Install chezmoi and apply dotfiles
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply bultot/dotfiles
```

## Bootstrap (full setup)

```sh
# Clone, install tools, apply configs
./scripts/bootstrap.sh
```

## Directory Layout

```
.chezmoi.toml.tmpl   # Machine-specific config (name, email, machine type)
Brewfile              # Homebrew package declarations
scripts/              # Bootstrap and utility scripts
home/                 # chezmoi source directory (maps to ~/)
  dot_config/
    zsh/              # Shell config files (exports, aliases, functions, plugins)
    ghostty/          # Terminal emulator config
    starship.toml     # Prompt theme
  dot_gitconfig       # Git config with per-domain identity
  dot_zshrc           # Minimal zsh entry point
  dot_tmux.conf       # tmux configuration
```

## What's Managed

- Shell: zsh with starship prompt, aliases, fzf, zoxide, bat, eza, ripgrep
- Git: config with auto-selecting identity per domain (personal vs work)
- Terminal: Ghostty with long-session optimizations
- tmux: session persistence for agent teams
- Homebrew: all CLI tools and casks declared in Brewfile
