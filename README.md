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

The legacy `dotfiles` repository is archived and retained only for provenance/rollback archaeology. Zsh, Tmux, SSH client policy, and orchestration now have explicit canonical owners.

## Profiles

- `vps-minimal`: Zsh + Tmux + Neovim
- `linux-dev`: Zsh + Tmux + Neovim
- `wsl-dev`: Zsh + Tmux + Neovim
- `windows-main`: Neovim + Rime + SSH client aliases; the profile is fully declarative and PowerShell-backed where installation work is required

## Usage

```bash
python3 scripts/configctl.py validate
python3 scripts/configctl.py plan vps-minimal
python3 scripts/configctl.py apply vps-minimal
```

`apply` supports Linux, WSL, and Windows Git-backed artifacts. It clones missing repositories, fast-forwards clean clones, refuses to overwrite dirty clones, and then delegates installation to the config repository's own installer when configured.

A `null` install action means the checkout path itself is the consumed configuration (for example Neovim). `manual` remains valid only for catalog artifacts that are not selected by a composed profile. Profile validation rejects manual install steps so a declared host profile is reproducible end to end.
