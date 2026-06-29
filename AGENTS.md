# AGENTS.md — kubuntu-ani-cursor-tool

## Project identity

- **Purpose**: Convert Windows `.ani`/`.cur` cursor files to KDE cursor theme archives (`.tar.gz`)
- **Repo root**: clone location — no hardcoded paths assumed
- **Language**: Python 3.13
- **Entry point**: `src/main.py`
- **Runtime dep**: `win2xcur` (nixpkgs, called as subprocess — NOT imported as a library)
- **Environment**: Nix flake + direnv (`flake.nix`, `.envrc`)

## File map

```
flake.nix                                  Nix dev shell + installable package
flake.lock
.envrc                                     "use flake" only
src/main.py                                CLI tool — all logic lives here
.agents/skills/convert-cursors/SKILL.md    AI skill for cursor conversion
.claude -> .agents                         Symlink (Claude Code reads .claude/)
AGENTS.md                                  This file
CLAUDE.md -> AGENTS.md                     Symlink
README.md                                  Human-facing docs
```

## CLI interface

```
python src/main.py [OPTIONS] [ROLE:]FILE [...]
```

### Options

| Flag | Short | Default | Notes |
|------|-------|---------|-------|
| `--name THEME` | `-n` | (required) | Theme directory name inside the archive |
| `--archive FILE` | `-a` | `./<THEME>.tar.gz` | Output archive path |
| `--role ROLE` | `-r` | auto from filename | Role override — **single file only**; error if >1 file given |
| `--list-roles` | | | Print roles table and exit |

`--output` does not exist. The tool writes nothing to `~/.local/share/icons/`; output is always a `.tar.gz`.

### Positional arguments

Each arg is `[ROLE:]FILE`. Detection logic (`src/main.py:283–291`):

1. If arg contains `:` at position > 1 AND the full string is not an existing path → split on first `:` via `parse_mapping()`
2. Otherwise → plain path; role from `--role` or `guess_role(path)`

`guess_role` (`src/main.py:189`) looks up `path.stem.lower()` in `FILENAME_ROLE_MAP`.  
Unknown stems fall back to `"arrow"`.

Duplicate role detection (`src/main.py:295–309`): if the same role appears more than once in the final mappings list, a warning is printed before conversion begins. The last assignment wins.

## Key data structures

### `XCURSOR_ALIASES` (`src/main.py:14`)

`dict[str, list[str]]` — 15 semantic roles → list of X cursor names.  
`aliases[0]` is the **canonical** filename written to disk.  
`aliases[1:]` are symlinks pointing to `aliases[0]`.

Roles: `arrow`, `help`, `working`, `wait`, `crosshair`, `text`, `pen`, `unavailable`, `size_ns`, `size_ew`, `size_nwse`, `size_nesw`, `move`, `up_arrow`, `link`

### `_ALL_XCURSOR_NAMES` (`src/main.py:94`)

`frozenset[str]` — flat set of every X cursor name across all roles.  
Built once at module load. Used for O(1) unknown-role validation in `main()`.

### `FILENAME_ROLE_MAP` (`src/main.py:105`)

`dict[str, str]` — lowercase filename stem → role name.  
Used by `guess_role()`. Add entries here to support new auto-detection patterns.

## Conversion pipeline

```
input .ani/.cur
  └─ convert_file()  (src/main.py:152)
       └─ subprocess: win2xcur <input> -o <tmpdir>
       └─ warns if win2xcur emits >1 output file, uses outputs[0]
  └─ install_cursor()  (src/main.py:174)
       └─ writes bytes to cursors_dir / aliases[0]
       └─ creates symlinks for aliases[1:]
  └─ writes index.theme
  └─ create_archive()  (src/main.py:205)
       └─ tar.gz of theme_dir, arcname=theme_dir.name
       └─ symlinks are preserved (tarfile default)
  └─ TemporaryDirectory is cleaned up automatically
```

Output: a single `.tar.gz` archive. Archive structure:

```
<THEME>/
├── index.theme
└── cursors/
    ├── default          ← canonical file (arrow role)
    ├── left_ptr -> default
    └── ...
```

`index.theme` format (cursor theme — minimal, no `Directories` section):

```ini
[Icon Theme]
Name=ThemeName
Comment=ThemeName cursor theme (converted from Windows cursors)
```

## AI Agent Skill

`.agents/skills/convert-cursors/SKILL.md` (symlinked as `.claude/skills/convert-cursors/SKILL.md` for Claude Code compatibility) — invoked as `/convert-cursors`.

Accepts optional arguments: `/convert-cursors [theme-name] [zip-or-directory]`.

Workflow:
1. Lists `.ani`/`.cur` files from a zip or directory (extracts zip to a temp dir)
2. Infers roles from filenames (English and Japanese); asks user for ambiguous cases
3. Presents full mapping for user approval before conversion
4. Runs `src/main.py` and reports the archive path + final mapping table
5. Cleans up temp dir; reports failure and asks user to delete manually if `rm -rf` fails

## Nix environment

`flake.nix` provides:

- `devShells.default`: `pkgs.python3` + `pkgs.win2xcur` in PATH
- `packages.default`: installable wrapper (`nix run .`) that calls `python3 src/main.py`

`win2xcur` is called as a subprocess to avoid PYTHONPATH management for its transitive deps (`wand`, `numpy`).

## Common tasks

**Add a new filename auto-detection pattern**  
→ Add `"stem": "role"` to `FILENAME_ROLE_MAP` at `src/main.py:105`.

**Add a new cursor role**  
→ Add `"role_name": ["canonical", "alias1", ...]` to `XCURSOR_ALIASES` at `src/main.py:14`. `_ALL_XCURSOR_NAMES` is rebuilt automatically at module load.

**Change the output `index.theme` content**  
→ Edit `INDEX_THEME_TEMPLATE` at `src/main.py:99`. Keep it to `[Icon Theme]` + `Name` + `Comment` only — `Directories` sections break KDE cursor theme detection.

**Test without dev shell**  
→ Prefix PATH with win2xcur's nix store bin dir:
```bash
PATH="$(nix build nixpkgs#win2xcur --no-link --print-out-paths)/bin:$PATH" python3 src/main.py ...
```

## Constraints

- Requires `win2xcur` in PATH at runtime; `find_win2xcur()` (`src/main.py:142`) raises `RuntimeError` (not `sys.exit`) if missing — caught and converted in `main()`.
- Python 3.10+ required (`dict[str, ...]` syntax requires 3.9+, subprocess+tempfile use standard library).
- Symlinks are POSIX-only. Windows is not a target.
- No files are written outside the temp directory and the output archive path.
- Re-running with the same `--archive` path overwrites the archive.
