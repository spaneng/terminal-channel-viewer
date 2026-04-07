# Terminal Channel Viewer

A terminal UI for viewing and monitoring Doover DDA channel data in real time.

Built with [Textual](https://textual.textualize.io/) and [pydoover](https://github.com/getdoover/pydoover).

## Installation

Requires Python 3.12+.

```bash
git clone https://github.com/spaneng/terminal-channel-viewer.git
cd terminal-channel-viewer
uv sync
```

## Usage

```bash
uv run channel-viewer <dda-host>
```

For example:

```bash
uv run channel-viewer 10.144.226.144
```

### Filter to a single key

```bash
uv run channel-viewer 10.144.226.144 --key pressure
```

### Set up a shell alias

Add this to your `~/.zshrc` or `~/.bashrc` for quick access:

```bash
alias cv="uv run --project /path/to/terminal-channel-viewer channel-viewer"
```

Then just run:

```bash
cv 10.144.226.144
```

## Keybindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `s` | Star/unstar the highlighted row |
| Arrow keys | Navigate rows and channels |
| Enter | Select a channel from the sidebar |

## Features

- **Channel sidebar** -- lists all channels on the DDA. Select one to view its data.
- **Live updates** -- values update in real time via gRPC streaming.
- **Starred values** -- press `s` to pin any value to the starred table at the bottom. Starred values stay visible and keep updating regardless of which channel you're viewing.
- **Nested key flattening** -- nested dicts are shown with dot notation (e.g. `pump_state.running`).
- **Alphabetical sorting** -- keys and first-level nested keys are sorted alphabetically.
