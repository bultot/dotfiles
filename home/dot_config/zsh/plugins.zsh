# Zsh plugins - loaded via Homebrew-installed paths
# zsh-autosuggestions: suggests commands as you type (grey text)
# zsh-syntax-highlighting: colors valid/invalid commands

# Note: install via Homebrew:
#   brew install zsh-autosuggestions zsh-syntax-highlighting

# Autosuggestions
if [[ -f "$HOMEBREW_PREFIX/share/zsh-autosuggestions/zsh-autosuggestions.zsh" ]]; then
    source "$HOMEBREW_PREFIX/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
fi

# Syntax highlighting (must be last)
if [[ -f "$HOMEBREW_PREFIX/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]]; then
    source "$HOMEBREW_PREFIX/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
fi
