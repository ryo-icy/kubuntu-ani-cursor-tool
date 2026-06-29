#!/usr/bin/env python3
"""Convert Windows .ani/.cur cursor files into a KDE/X11 cursor theme."""

import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

# Mapping from semantic cursor roles to canonical X cursor names + aliases.
# Derived from win2xcur's theme.py (version 0.2.1).
XCURSOR_ALIASES: dict[str, list[str]] = {
    "arrow": [
        "default", "arrow", "left_ptr", "top_left_arrow",
        "left-arrow", "right-arrow", "down-arrow",
        "sb_left_arrow", "sb_right_arrow", "sb_down_arrow",
        "grab", "openhand",
        "alias", "link", "dnd-link",
        "3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ed57b41487f",
        "a2a266d0498c3104214a47bd64ab0fc8",
        "top_left_corner", "top_right_corner", "bottom_left_corner", "bottom_right_corner",
        "top_side", "bottom_side", "left_side", "right_side",
        "ul_angle", "ur_angle", "ll_angle", "lr_angle",
        "right_ptr", "draft_large", "draft_small",
        "vertical-text",
        "copy", "dnd-copy",
        "1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872",
        "b66166c04f8c3109214a4fbd64a50fc8",
        "zoom-in", "zoom-out",
        "dotbox", "dot_box_mask", "draped_box", "icon", "target",
        "context-menu", "center_ptr", "color-picker", "X_cursor", "x-cursor",
        "wayland-cursor", "pirate",
        "top_tee", "bottom_tee", "left_tee", "right_tee",
    ],
    "help": [
        "help", "left_ptr_help", "question_arrow", "whats_this",
        "5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b",
    ],
    "working": [
        "progress", "half-busy", "left_ptr_watch",
        "00000000000000020006000e7e9ffc3f",
        "08e8e1c95fe2fc01f976f1e063a24ccd",
        "3ecb610c1bf2410f44200f48c40d3599",
    ],
    "wait": ["wait", "watch"],
    "crosshair": [
        "crosshair", "cross", "tcross", "cross_reverse", "diamond_cross",
        "cell", "plus",
    ],
    "text": ["text", "ibeam", "xterm"],
    "pen": ["pencil", "draft"],
    "unavailable": [
        "not-allowed", "circle", "crossed_circle",
        "03b6e0fcb3499374a867c041f52298f0",
        "forbidden", "no-drop", "dnd-no-drop",
    ],
    "size_ns": [
        "size_ver", "size-ver", "ns-resize", "n-resize", "s-resize",
        "v_double_arrow", "sb_v_double_arrow", "row-resize", "split_v",
        "double_arrow", "00008160000006810000408080010102",
        "2870a09082c103050810ffdffffe0204",
    ],
    "size_ew": [
        "size_hor", "size-hor", "ew-resize", "e-resize", "w-resize",
        "h_double_arrow", "sb_h_double_arrow", "col-resize", "split_h",
        "14fef782d02440884392942c11205230", "028006030e0e7ebffc7f7070c0600140",
    ],
    "size_nwse": [
        "size_fdiag", "size-fdiag", "nwse-resize", "nw-resize", "se-resize",
        "bd_double_arrow", "c7088f0f3e6c8088236ef8e1e3e70000",
    ],
    "size_nesw": [
        "size_bdiag", "size-bdiag", "nesw-resize", "ne-resize", "sw-resize",
        "fd_double_arrow", "fcf1c3c7cd4491d801f1e1c78f100000",
    ],
    "move": [
        "fleur", "size_all", "all-scroll",
        "move", "grabbing", "closedhand", "dnd-move", "dnd-none", "dnd-ask",
        "4498f0e0c1937ffe01fd06f973665830",
        "9081237383d90e509aa00f00170e968f",
        "fcf21c00b30f7e3f83fe0dfd12e71cff",
    ],
    "up_arrow": ["up-arrow", "sb_up_arrow"],
    "link": [
        "pointer", "pointing_hand", "hand", "hand1", "hand2",
        "9d800788f1b08800ae810202380a0822",
        "e29285e634086352946a0e7090d73106",
    ],
}

# Flat set of all known X cursor names for O(1) lookup.
_ALL_XCURSOR_NAMES: frozenset[str] = frozenset(
    name for aliases in XCURSOR_ALIASES.values() for name in aliases
)

INDEX_THEME_TEMPLATE = """\
[Icon Theme]
Name={name}
Comment={name} cursor theme (converted from Windows cursors)
"""

# Filename stem -> role heuristics
FILENAME_ROLE_MAP = {
    "arrow": "arrow",
    "aero_arrow": "arrow",
    "default": "arrow",
    "left_ptr": "arrow",
    "wait": "wait",
    "busy": "wait",
    "aero_busy": "wait",
    "working": "working",
    "aero_working": "working",
    "help": "help",
    "aero_helpsel": "help",
    "hand": "link",
    "pointer": "link",
    "text": "text",
    "beam": "text",
    "ibeam": "text",
    "cross": "crosshair",
    "crosshair": "crosshair",
    "move": "move",
    "aero_move": "move",
    "size_ns": "size_ns",
    "size_ew": "size_ew",
    "size_nwse": "size_nwse",
    "size_nesw": "size_nesw",
    "sizens": "size_ns",
    "sizewe": "size_ew",
    "sizenwse": "size_nwse",
    "sizenesw": "size_nesw",
    "no": "unavailable",
    "unavailable": "unavailable",
    "pen": "pen",
    "aero_pen": "pen",
    "up_arrow": "up_arrow",
}


def find_win2xcur() -> str:
    path = shutil.which("win2xcur")
    if path is None:
        raise RuntimeError(
            "win2xcur not found in PATH.\n"
            "Run 'direnv allow' in the project root to enter the dev shell, or 'nix develop'."
        )
    return path


def convert_file(input_path: Path, win2xcur_bin: str) -> bytes:
    """Run win2xcur on input_path and return the raw X11 cursor bytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [win2xcur_bin, str(input_path), "-o", tmpdir],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "win2xcur failed")
        outputs = list(Path(tmpdir).iterdir())
        if not outputs:
            raise RuntimeError("win2xcur produced no output")
        if len(outputs) > 1:
            names = [f.name for f in outputs]
            print(
                f"Warning: win2xcur produced {len(outputs)} files {names}, using {outputs[0].name}",
                file=sys.stderr,
            )
        return outputs[0].read_bytes()


def install_cursor(data: bytes, role: str, cursors_dir: Path) -> int:
    """Write cursor data and create symlinks. Returns symlink count."""
    aliases = XCURSOR_ALIASES.get(role, [role])
    canonical = aliases[0]
    (cursors_dir / canonical).write_bytes(data)

    for alias in aliases[1:]:
        link = cursors_dir / alias
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(canonical)

    return len(aliases) - 1


def guess_role(path: Path) -> str:
    return FILENAME_ROLE_MAP.get(path.stem.lower(), "arrow")


def parse_mapping(value: str) -> tuple[str, Path]:
    """Parse a 'role:path' string into (role, path)."""
    role, _, raw_path = value.partition(":")
    return role.strip(), Path(raw_path.strip())


def list_roles() -> None:
    print("Available cursor roles:")
    for role, aliases in XCURSOR_ALIASES.items():
        print(f"  {role:12s}  canonical={aliases[0]}  ({len(aliases)-1} symlinks)")


def create_archive(theme_dir: Path, dest: Path) -> None:
    """Pack theme_dir into a .tar.gz suitable for KDE 'Install from file'."""
    with tarfile.open(dest, "w:gz") as tar:
        tar.add(theme_dir, arcname=theme_dir.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ani-cursor-tool",
        description="Convert Windows .ani/.cur files to a KDE/X11 cursor theme.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single .ani file -> auto-detect role from filename, output MyTheme.tar.gz
  ani-cursor-tool --name MyTheme cursor.ani

  # Explicit role via --role (single file only)
  ani-cursor-tool --name MyTheme --role wait busy.ani

  # role:file syntax for multiple files
  ani-cursor-tool --name MyTheme arrow:cursor.ani wait:busy.ani help:help.ani

  # Custom archive output path
  ani-cursor-tool --name MyTheme --archive ~/themes/MyTheme.tar.gz arrow:cursor.ani

  # List all cursor roles and their X11 names
  ani-cursor-tool --list-roles
""",
    )
    parser.add_argument(
        "--name", "-n",
        metavar="THEME_NAME",
        help="Cursor theme name (required unless --list-roles)",
    )
    parser.add_argument(
        "--archive", "-a",
        metavar="FILE.tar.gz",
        help="Output archive path (default: ./<THEME_NAME>.tar.gz)",
    )
    parser.add_argument(
        "--role", "-r",
        metavar="ROLE",
        help="Cursor role for a single input file; error if multiple files are given",
    )
    parser.add_argument(
        "--list-roles",
        action="store_true",
        help="Print available cursor roles and exit",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="[ROLE:]FILE",
        help="Files to convert. Prefix with 'role:' to set the role (e.g. arrow:cursor.ani).",
    )

    args = parser.parse_args()

    if args.list_roles:
        list_roles()
        return

    if not args.name:
        parser.error("--name / -n is required")

    if not args.files:
        parser.error("At least one input file is required")

    if args.role and len(args.files) > 1:
        parser.error("--role / -r can only be used with a single input file")

    try:
        win2xcur_bin = find_win2xcur()
    except RuntimeError as exc:
        sys.exit(f"Error: {exc}")

    # Build list of (role, path) pairs
    mappings: list[tuple[str, Path]] = []
    for entry in args.files:
        colon_pos = entry.find(":")
        looks_like_role_prefix = colon_pos > 1  # "arrow:foo.ani" yes, "C:\..." no
        if looks_like_role_prefix and not Path(entry).exists():
            role, path = parse_mapping(entry)
        else:
            path = Path(entry)
            role = args.role if args.role else guess_role(path)
        mappings.append((role, path))

    # Validate inputs
    seen_roles: dict[str, str] = {}
    for role, path in mappings:
        if role not in XCURSOR_ALIASES and role not in _ALL_XCURSOR_NAMES:
            print(f"Warning: unknown role '{role}' - will be used as a literal cursor name", file=sys.stderr)
        if role in seen_roles:
            print(
                f"Warning: role '{role}' assigned to both '{seen_roles[role]}' and '{path.name}' - "
                f"'{seen_roles[role]}' will be overwritten",
                file=sys.stderr,
            )
        seen_roles[role] = path.name
        if not path.exists():
            sys.exit(f"Error: file not found: {path}")
        if path.suffix.lower() not in (".ani", ".cur"):
            print(f"Warning: {path.name} has unexpected extension (expected .ani or .cur)", file=sys.stderr)

    archive_path = Path(args.archive) if args.archive else Path(f"{args.name}.tar.gz")

    with tempfile.TemporaryDirectory() as tmpdir:
        theme_dir = Path(tmpdir) / args.name
        cursors_dir = theme_dir / "cursors"
        cursors_dir.mkdir(parents=True)

        print(f"Converting {len(mappings)} file(s) for theme '{args.name}' ...")
        for role, path in mappings:
            print(f"  {path.name} -> role '{role}' ...", end=" ", flush=True)
            try:
                data = convert_file(path, win2xcur_bin)
                n_links = install_cursor(data, role, cursors_dir)
                print(f"ok  ({n_links} symlinks)")
            except Exception as exc:
                print("FAILED")
                sys.exit(f"Error: {exc}")

        (theme_dir / "index.theme").write_text(INDEX_THEME_TEMPLATE.format(name=args.name))
        create_archive(theme_dir, archive_path)

    print(f"\nCreated: {archive_path.resolve()}")
    print("Install: KDE System Settings -> Cursors -> Install from file")


if __name__ == "__main__":
    main()
