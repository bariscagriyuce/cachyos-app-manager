# CachyOS App Manager

A simple graphical tool for **viewing, searching and uninstalling installed packages** on CachyOS (and other Arch-based distros) — no need to remember `pacman` commands.

The interface is in Turkish.

## Features

- **Categories** in the sidebar, each with a package count:
  - **Desktop Applications** – packages that ship a visible `.desktop` launcher (what you see in your app menu)
  - **CachyOS Repository** – packages from `cachyos`, `cachyos-v3`, `cachyos-core-v3`, `cachyos-extra-v3`, …
  - **Arch Repository** – packages from `core`, `extra`, `multilib`
  - **AUR / Foreign** – packages not found in any sync repo (`pacman -Qm`)
  - **Other Repositories** – any custom repos (shown only if present)
  - **All**
- **Instant search** across app name, package name and description (`Ctrl+F`).
- **One-click uninstall** of one or more selected packages (`Delete` key or button):
  - Shows a preview of everything that will be removed, including orphaned dependencies, and how much space will be freed.
  - Uses `pkexec` for a graphical password prompt, then runs `pacman -Rns` with live output.
  - If other packages depend on the selection, it explains which ones instead of failing silently.
  - Extra warning for critical system packages (`glibc`, `systemd`, kernels, `plasma-desktop`, …).
- **Clean orphans** – remove dependencies that nothing needs anymore (`pacman -Qdt`).
- Package details (`pacman -Qi`) on double-click, sortable columns (e.g. by size), right-click menu.
- Packages installed as dependencies are hidden by default; toggle them with the checkbox.

## Requirements

- Python 3
- PyQt6 (`python-pyqt6`)
- `pacman`, `expac`, `polkit` (`pkexec`)

```bash
sudo pacman -S --needed python-pyqt6 expac polkit
```

All of these are installed by default on CachyOS KDE.

## Usage

```bash
git clone https://github.com/bariscagriyuce/cachyos-app-manager.git
cd cachyos-app-manager
python3 cachyos_app_manager.py
```

### Add to the application menu

Edit the `Exec=` line in `cachyos-app-manager.desktop` so it points to where you cloned the repo, then:

```bash
cp cachyos-app-manager.desktop ~/.local/share/applications/
```

## How it works

| Information | Source |
|---|---|
| Installed packages, version, size, description | `expac -Q '%n\t%v\t%m\t%d'` |
| Which repo a package came from | `pacman -Sl` (first repo whose version matches the installed one) |
| AUR / foreign packages | `pacman -Qqm` |
| Explicitly installed vs. dependency | `pacman -Qqe` |
| App name and icon | `.desktop` files listed in `/var/lib/pacman/local/*/files` |
| Removal preview | `pacman -Rs -p` (dry run, no root needed) |
| Removal | `pkexec pacman -Rns --noconfirm <packages>` |

The app only reads data as a normal user; root privileges are requested through polkit only when you confirm a removal.
