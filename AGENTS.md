# Agent Guide: Story Packs

Use this file when creating or expanding a `opengame` story pack.

## Core Paradigm: Linear Storytelling

`opengame` is a Python CLI narrative engine. Story packs are **linear** by default — the player progresses scene by scene through a predetermined sequence. No hubs, no character-based routing, no conditional gating.

The pack is organized into **arcs** — logical chapters that define a clear beginning, middle, and end. Each arc chains into the next via `next` references on the last step or option, forming one continuous narrative thread.

## Pack Shape

```
content/sample_game/
  game.yaml
  variables.yaml
  items.yaml           ← optional
  quests.yaml          ← optional
  npcs.yaml            ← optional
  arcs/
    01_opening.yaml     ← arc 1: awakening in a strange new world
    02_dungeon.yaml     ← arc 2: dungeon exploration, treasure
```

Only `game.yaml` and `arcs/` are required. The loader prefers `arcs/` but falls back to `scenes/` for legacy packs.

## Arc Planning (ARC_PLANNING.md)

**Before writing any YAML files**, plan the entire story by dividing it into ARCs and save the outline to `ARC_PLANNING.md`. This ensures the full narrative is designed end-to-end before implementation begins.

Define each ARC with a clear **scope** (the sequence of narrative beats it covers) and a scene count. List every scene with a descriptive paragraph of what happens.

Scenes should typically land in the 10–20 step range; aim for ~15 steps per scene, adjusting based on narrative needs.

```markdown
# ARC_PLANNING — Sample Game

## ARC 1: AWAKENING IN FOOTHOLD
**Scope**: Waking up in a new world → exploring the market → dungeon beckons

### Scenes (6):
1. **start_game** — You wake in a strange world. Pila greets you warmly, offers food.
2. **visit_shop** — The bustling market. Mira at her weapons stall offers two paths: browse her wares or ask about the dungeon.

## ARC 2: THE DUNGEON
**Scope**: Dungeon entrance → first hall → treasure chamber

### Scenes (3):
1. **arc2_dungeon_entrance** — The cave mouth looms. Cold air. You step into darkness.
2. **arc2_dungeon_hall** — A vast hall with three passages. A giant rat attacks.
3. **ending_victory** — Treasure glints ahead. Foothold will be pleased.
```

Only after the full `ARC_PLANNING.md` is approved should implementation of individual arc files begin.

## Pack Files

`game.yaml` defines metadata and the start scene:

```yaml
id: test_arcs
title: Test Arcs
version: 1
start_scene: start_game
author: opengame
description: Testing arcs/ directory loading.
```

`variables.yaml` declares every flag and counter before scenes use them:

```yaml
flags:
  met_pila: false
counters:
  trust: 0
```

## Scene Format

Scenes support two formats: **stepped** (`steps`) and **flat** (`text` + `choices`). Stepped scenes are recommended and should be the default choice for all new content.

### Stepped Scenes

A scene with a `steps` list. Each step is one screenful of narration or character dialogue. The player advances through steps by pressing **Next** or selecting options.

```yaml
- id: start_game
  title: The Beginning
  steps:
    - text: You open your eyes in a strange new world.

    - text: Ah, you're awake. Welcome.
      author: Pila

    - text: She smiles warmly. You feel safe here.
      options:
        - text: Thank her
          response:
            text: Let's get you something to eat.
            author: Pila
        - text: Ask where you are
          response:
            text: This is an adventurer's town.
            author: Pila

    - text: Let's get you something to eat.
      author: Pila

    - text: She gestures toward the market.
      next: visit_shop           # chains to the next scene
```

**All step fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | yes | The text displayed for this step |
| `author` | string | no | Speaker name. Absent = narrator. |
| `options` | list | no | Inline player choices for this step |
| `next` | string | no | Auto-navigate to this scene ID after displaying the text |

**Option fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | yes | The choice label |
| `response` | mapping or list | no | Inline reply text (a step or list of steps) |
| `next` | string | no | Navigate to this scene ID after the response (or immediately, if no response) |
| `conditions` | list | no | Condition checks |
| `effects` | list | no | State mutations |

**Step flow rules:**

- **No author** = narrator text. Displayed as plain panel body.
- **Author present** = character speech. The engine displays the author name in magenta.
- **No options, no `next`** = the engine generates a single `Next` choice. Player presses Enter to advance.
- **Options present** = player picks one. If the option has a `response`, the response steps play. Then the engine either navigates to `next_scene` (if set) or advances to the next step.
- **`next` on the step itself** = auto-advance. Text is displayed, then immediately transitions to the target scene.
- **Empty-text step with `next`** = silent transition between scenes.
- An option's `response` can be a **single step** or a **list of steps**.

**Response as a list of steps:**

```yaml
options:
  - text: Tell me more
    response:
      - text: Well, I used to be a knight.
        author: Mira
      - text: But that was a long time ago.
        author: Mira
```

**Conditions and effects on options:**

```yaml
options:
  - text: Unlock the chest
    conditions:
      - has_item: brass_key
    effects:
      - add_item: silver_ring
    next: treasure_room
```

### Flat Scenes (legacy)

Use sparingly, only for simple decision-heavy moments. A single mapping with `id`, `title`, `text`, and `choices`:

```yaml
- id: forks
  title: A Choice
  text: |
    Three paths stretch before you.
  choices:
    - text: Take the forest path
      target: forest_clearing
    - text: Head toward the village
      target: village_gate
```

Each flat choice must use exactly one destination: `target` for a scene or `dialogue` for an NPC dialogue.

## Arc Files

Arc files live in `arcs/` (or `scenes/` for legacy packs). Each arc file is a YAML list of stepped scenes — a self-contained chapter of the story.

Name arc files with a numeric prefix and a descriptive name that captures the arc's content:

```
arcs/
  01_opening.yaml       ← arrival, meeting the cast
  02_dungeon.yaml       ← dungeon exploration, treasure
```

**Every arc must follow the stepped format shown in this guide:**

1. **Stepped scenes only** — no flat scenes in arc files.
2. **Linear chain** — each scene links to the next via `next` on the last step or last option.
3. **Narrator steps guide the player** — use `text` without `author` to set the scene, describe actions, and convey internal thoughts.
4. **Character dialogue uses `author`** — every character line gets an `author` field. This makes their personality distinct through their voice alone.
5. **Options appear only where the player has a meaningful choice** — ask a question, take a story branch, or set a flag. Most steps should be pure narration with `Next` to advance.
6. **The last step of each arc links to the first scene of the next arc** — use `next: first_scene_id_of_next_arc` on the final option or final step.

**Example arc file:**

```yaml
# arcs/01_opening.yaml

- id: start_game
  title: The Beginning
  steps:
    - text: You open your eyes in a strange new world.
    - text: Ah, you're awake. Welcome.
      author: Pila
    - text: She smiles warmly. You feel safe here.
    - text: Let's get you something to eat.
      author: Pila
      next: visit_shop

- id: visit_shop
  title: The Market
  steps:
    - text: The market is bustling with merchants and adventurers.
    - text: A girl at a weapons stall catches your eye.
    - text: Need a blade, stranger?
      author: Mira
      options:
        - text: Browse her wares
          response:
            text: Take your time. These are all hand-forged.
            author: Mira
          next: arc2_dungeon_entrance
        - text: Ask about the dungeon
          response:
            text: The dungeon? You're brave. Or foolish.
            author: Mira
          next: arc2_dungeon_entrance
```

**Arc chaining rules:**

- The final scene of arc N must link to the first scene of arc N+1. Use `next` on the last step or last option.
- Arc files are loaded in alphabetical order. The numeric prefix (`01_`, `02_`, ...) ensures correct sequencing.
- Scene IDs must be unique across the entire pack — even across arc files.
- Use lowercase `snake_case` for all IDs.
- Every non-ending scene needs at least one choice point (an option) or a `next` link. A scene that dead-ends with no way forward is an error.

### Linear Flow Pattern

The narrative flows in one direction: **start → arc 1 scene 1 → arc 1 scene 2 → ... → arc 2 scene 1 → ... → ending**.

```mermaid
arc 1: scene_a → scene_b → scene_c
                              ↓  (next: arc2_scene_d)
arc 2:               scene_d → scene_e → scene_f → ending
```

Within a single arc, scenes chain by `next`. Between arcs, the last scene of one arc chains to the first scene of the next. No scene should ever link backward or loop to a hub.

### Writing Arc Files

When writing or expanding an arc file:

1. Read the sample_game arc files for style reference — they're the canonical examples.
2. Read `game.yaml` and `variables.yaml` of the target pack.
3. Read only the arc files directly before and after the arc you're editing, so you know entry and exit points.
4. Write each scene as a stepped scene with `id`, `title`, and `steps`.
5. Every step that isn't a transition should have prose — describe the setting, actions, emotions.
6. Use `author: Player` for player dialogue. The engine renders it like NPC dialogue, helping the player inhabit their character.
7. Validate before finishing:

```powershell
opengame validate content/sample_game
```

If the console script is unavailable:

```powershell
python -m opengame validate content/sample_game
```

If the console script is unavailable:

```powershell
python -m opengame validate content/sample_game
```

## Speaker Attribution

Use `author` on steps to give dialogue to a character. The engine renders the speaker name in magenta above the text. Omit `author` for narrator prose.

```yaml
steps:
  # narrator — plain text
  - text: The door creaks open. A figure steps into the light.

  # character speech — magenta name above text
  - text: I've been waiting for you.
    author: Mira

  # player dialogue
  - text: I didn't mean to keep you waiting.
    author: Player

  # back to narrator
  - text: She crosses her arms, sizing you up.
```

## Conditions And Effects

Supported conditions:

- `flag` with `equals`
- `counter` with `equals`
- `has_item`
- `quest_status: { quest, equals }`
- `relationship: { npc, at_least }`

Supported effects:

- `set: { flag, value }`
- `increment: { counter, amount }`
- `add_item: item_id`
- `remove_item: item_id`
- `start_quest: quest_id`
- `complete_quest: quest_id`
- `fail_quest: quest_id`
- `set_quest_status: { quest, status }`
- `change_relationship: { npc, amount }`
- `set_relationship: { npc, value }`

Quest statuses must be `inactive`, `active`, `completed`, or `failed`.

Conditions and effects can appear on flat scene choices and on stepped scene options.

## Writing Guidance

### Scene Text Style

- Write vivid, descriptive text. Use detailed physical descriptions: settings, objects, actions, expressions. Paint a clear picture for the player.
- Use the narrator voice for internal thoughts, sensory details, and scene-setting. Use `author` for spoken dialogue only.
- Keep steps short — 1-3 sentences per step. The player should feel a rhythm of reading → pressing Next.
- Mix narrator and dialogue steps to create a natural conversational flow.
- Use `Player` as the author for the player character's spoken lines.

### General Rules

- Prefer stepped scenes for everything. Flat scenes are for legacy compatibility only.
- Write small, focused scenes — 10-20 steps each. One scene = one narrative beat.
- Make branches rejoin when possible. If you split on a choice, merge back within the same arc.
- Avoid orphan scenes unless intentionally unreachable for future work.
- Preserve existing tone, tense, and naming style when expanding a pack.
- Validate after every structural change and fix all reported issues.
- Endings — use a flat scene with `ending: true` or a stepped scene whose last step has no forward link.
- When a pack is designed to be continued later, do not mark any scene with `ending: true`. The last scene simply has no options — the engine will display "No available choices."
