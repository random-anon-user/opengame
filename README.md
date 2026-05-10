# opengame

A Python CLI text-based narrative game engine powered by modular YAML content. Write story packs as YAML files and play them in the terminal.

## Installation

Requires Python 3.11+.

```bash
# Install from source (editable, recommended for development)
pip install -e .

# Or install with dev dependencies (pytest)
pip install -e ".[dev]"
```

## Usage

### Play a story pack

```bash
# Play the built-in sample game
opengame play

# Play a specific story pack
opengame play path/to/your_pack
```

Supported controls during play:

| Key | Action |
|---|---|
| Arrow Up / Down | Navigate choices |
| Enter | Select choice |
| `q` | Quit |
| Ctrl+S | Save progress |
| Ctrl+T | Translate step text (requires `OPENAI_API_KEY`) |

Resume from a saved game:

```bash
opengame play --resume
opengame play --resume --save-file path/to/save.json
```

### Validate a story pack

```bash
opengame validate
opengame validate path/to/your_pack
```

### Inspect a story pack

```bash
opengame inspect
opengame inspect path/to/your_pack
```

## Writing story packs

Create a directory with a `game.yaml`, optional `variables.yaml`, and a set of scene/arc files:

```
my_game/
├── game.yaml          # metadata (id, title, start_scene, ...)
├── variables.yaml     # optional: flags, counters, items, quests, npcs
└── arcs/
    ├── 01_opening.yaml
    ├── 02_dungeon.yaml
    └── 03_ending.yaml
```

See `content/sample_game/` for a complete example.

## Commands

| Command | Description |
|---|---|
| `opengame play` | Play a story pack |
| `opengame validate` | Validate a story pack |
| `opengame inspect` | Show a story pack summary |
