# personal-config

Thin orchestration and host-profile repository for independently versioned personal software configurations.

This repository **does not own** Neovim, Zsh, Tmux, Rime, or Mihomo configuration content. Each substantial configuration keeps its own Git repository and lifecycle. `personal-config` answers only:

- which configuration artifacts exist;
- which host/profile consumes which artifacts;
- where they should be materialized;
- how to bootstrap/update them safely.

## Current canonical config repositories

- `nvim-config`
- `zsh-config`
- `tmux-config`
- `rime-config`
- `ssh-client-config`
- `mihomo-rules`

The legacy `dotfiles` repository remains a rollback source while SSH client policy and remaining orchestration are migrated.

## Profiles

- `vps-minimal`: Zsh + Tmux + Neovim
- `linux-dev`: Zsh + Tmux + Neovim
- `wsl-dev`: Zsh + Tmux + Neovim
- `windows-main`: Neovim + Rime + SSH client aliases; PowerShell-backed install actions are supported

## Usage

```bash
python3 scripts/configctl.py validate
python3 scripts/configctl.py plan vps-minimal
python3 scripts/configctl.py apply vps-minimal
```

`apply` currently supports Linux/WSL Git-backed artifacts with an explicit install command. It clones missing repositories, fast-forwards clean clones, refuses to overwrite dirty clones, and then delegates installation to the config repository's own installer when configured.
