#!/usr/bin/env python3
"""Safe, local-only file inventory and organization helpers.

The tool deliberately has no delete command. Mutating operations require explicit
flags and refuse overwrites, symlinks, protected structures, and cross-volume
moves.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator


APPROVAL_TOKEN = "COPY-AND-VERIFY"
FAT32_MAX_FILE = 4 * 1024**3 - 1
INSTALLER_SUFFIXES = {".dmg", ".pkg", ".iso"}
ARCHIVE_SUFFIXES = {".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".7z", ".rar"}
PROTECTED_SUFFIXES = {
    ".app",
    ".bundle",
    ".cmproj",
    ".fcpbundle",
    ".imovielibrary",
    ".photoslibrary",
    ".pvm",
    ".sparsebundle",
    ".utm",
    ".vmwarevm",
}
HIDDEN_PROTECTED_NAMES = {
    ".git",
    ".svn",
    ".hg",
    ".Spotlight-V100",
    ".Trashes",
    ".fseventsd",
}
ACTION_FIELDS = [
    "action_id",
    "batch",
    "action",
    "source",
    "destination",
    "reason",
    "confidence",
    "decision",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def default_run_dir() -> Path:
    return Path.home() / ".organize-files-safely" / "runs" / run_id()


def absolute_path(value: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(value))))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def protected_reason(path: Path) -> str:
    name = path.name
    lower_name = name.casefold()
    if path.is_symlink():
        return "symbolic link"
    if name.startswith("."):
        return "hidden item"
    if name in HIDDEN_PROTECTED_NAMES:
        return "hidden technical directory"
    if any(part in HIDDEN_PROTECTED_NAMES for part in path.parts):
        return "inside hidden technical directory"
    if lower_name.endswith(".icloud"):
        return "cloud placeholder"
    if path.suffix.casefold() in PROTECTED_SUFFIXES:
        return "protected package or project"
    if lower_name == "dicom" or lower_name == "dicomdir":
        return "DICOM structure"
    if path.is_dir():
        try:
            if (path / ".git").exists():
                return "Git repository"
            if (path / "DICOMDIR").exists() or (path / "dicomdir").exists():
                return "DICOM structure"
        except OSError:
            return "unreadable directory"
    return ""


def protected_descendant_reason(path: Path) -> str:
    """Return the first protected descendant without following links."""
    if not path.is_dir() or path.is_symlink():
        return ""
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in dirs + files:
            candidate = root_path / name
            reason = protected_reason(candidate)
            if reason:
                return f"contains {reason}: {candidate}"
        dirs[:] = [name for name in dirs if not protected_reason(root_path / name)]
    return ""


def item_record(path: Path, source_root: Path, depth: int) -> dict:
    try:
        info = path.lstat()
    except OSError as exc:
        return {
            "record_type": "error",
            "path": str(path),
            "source_root": str(source_root),
            "depth": depth,
            "error": str(exc),
        }

    if stat.S_ISLNK(info.st_mode):
        kind = "symlink"
    elif stat.S_ISDIR(info.st_mode):
        kind = "directory"
    elif stat.S_ISREG(info.st_mode):
        kind = "file"
    else:
        kind = "other"
    reason = protected_reason(path)
    try:
        relative = str(path.relative_to(source_root))
    except ValueError:
        relative = path.name
    return {
        "record_type": "item",
        "path": str(path),
        "source_root": str(source_root),
        "relative_path": relative,
        "name": path.name,
        "kind": kind,
        "size_bytes": info.st_size if kind == "file" else 0,
        "mtime_ns": info.st_mtime_ns,
        "depth": depth,
        "hidden": path.name.startswith("."),
        "protected": bool(reason),
        "protected_reason": reason,
    }


def scan_tree(source_root: Path, max_depth: int) -> Iterator[dict]:
    def visit(path: Path, depth: int) -> Iterator[dict]:
        record = item_record(path, source_root, depth)
        yield record
        if record.get("record_type") != "item":
            return
        if record["kind"] != "directory" or record["protected"] or depth >= max_depth:
            if record["kind"] == "directory" and depth >= max_depth:
                record["depth_limited"] = True
            return
        try:
            children = sorted(path.iterdir(), key=lambda child: child.name.casefold())
        except OSError as exc:
            yield {
                "record_type": "error",
                "path": str(path),
                "source_root": str(source_root),
                "depth": depth,
                "error": str(exc),
            }
            return
        for child in children:
            yield from visit(child, depth + 1)

    for top_level in sorted(source_root.iterdir(), key=lambda child: child.name.casefold()):
        yield from visit(top_level, 1)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_inventory(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def inventory_command(args: argparse.Namespace) -> int:
    output = absolute_path(args.output) if args.output else default_run_dir()
    output.mkdir(parents=True, exist_ok=False)
    sources: list[Path] = []
    for raw in args.source:
        source = absolute_path(raw)
        if not source.is_dir():
            raise SystemExit(f"Source is not a readable directory: {source}")
        sources.append(source)

    inventory_path = output / "inventory.jsonl"
    counts: defaultdict[str, int] = defaultdict(int)
    total_file_bytes = 0
    with inventory_path.open("w", encoding="utf-8") as handle:
        for source in sources:
            for record in scan_tree(source, args.max_depth):
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[record.get("record_type", "unknown")] += 1
                if record.get("record_type") == "item":
                    counts[record.get("kind", "unknown")] += 1
                    total_file_bytes += int(record.get("size_bytes", 0))

    summary = {
        "created_at": utc_now(),
        "sources": [str(path) for path in sources],
        "max_depth": args.max_depth,
        "counts": dict(counts),
        "scanned_file_bytes": total_file_bytes,
        "source_files_modified": False,
        "inventory": str(inventory_path),
    }
    write_json(output / "inventory-summary.json", summary)
    (output / "review.md").write_text(
        "# Inventory review\n\n"
        f"Created: {summary['created_at']}\n\n"
        f"Sources: {', '.join(summary['sources'])}\n\n"
        f"Depth: {args.max_depth}\n\n"
        f"Items: {counts['item']}  \nErrors: {counts['error']}  \n"
        f"Scanned file bytes: {total_file_bytes}\n\n"
        "No source file was intentionally modified. Review protected and depth-limited entries before planning.\n",
        encoding="utf-8",
    )
    print(output)
    return 0


def plan_command(args: argparse.Namespace) -> int:
    inventory = absolute_path(args.inventory)
    destination_root = absolute_path(args.destination_root)
    records = read_inventory(inventory)
    output = absolute_path(args.output) if args.output else inventory.parent / "actions.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    actions: list[dict[str, str]] = []
    index = 1
    for record in records:
        if record.get("record_type") != "item":
            continue
        protected = bool(record.get("protected"))
        actions.append(
            {
                "action_id": f"A{index:06d}",
                "batch": "unassigned",
                "action": "keep" if protected else "review",
                "source": record["path"],
                "destination": "",
                "reason": record.get("protected_reason") or "classification requires human review",
                "confidence": "high" if protected else "low",
                "decision": "locked" if protected else "pending",
            }
        )
        index += 1
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ACTION_FIELDS)
        writer.writeheader()
        writer.writerows(actions)
    review_path = inventory.parent / "review.md"
    review_path.write_text(
        "# Organization plan review\n\n"
        f"Inventory: `{inventory}`\n\n"
        f"Allowed destination root: `{destination_root}`\n\n"
        f"Rows: {len(actions)}\n\n"
        "The generated plan is conservative. Fill only reviewed `move` or `rename` actions, assign a batch, and set `decision=approved` only after the user approves that exact batch. Protected rows remain locked.\n",
        encoding="utf-8",
    )
    print(output)
    return 0


def nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return candidate


def append_journal(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": utc_now(), **payload}, ensure_ascii=False) + "\n")


def apply_command(args: argparse.Namespace) -> int:
    if not args.execute:
        raise SystemExit("Refusing to mutate files without --execute")
    plan_path = absolute_path(args.plan)
    allowed_root = absolute_path(args.allowed_root)
    with plan_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = [
        row
        for row in rows
        if row.get("batch") == args.batch
        and row.get("decision", "").casefold() == "approved"
        and row.get("action", "").casefold() in {"move", "rename"}
    ]
    if not selected:
        raise SystemExit(f"No approved move/rename actions found for batch: {args.batch}")

    prepared: list[tuple[dict[str, str], Path, Path]] = []
    failures: list[str] = []
    for row in selected:
        source = absolute_path(row["source"])
        destination = absolute_path(row["destination"])
        reason = protected_reason(source) if source.exists() or source.is_symlink() else ""
        descendant_reason = protected_descendant_reason(source) if source.exists() else ""
        if not source.exists() and not source.is_symlink():
            failures.append(f"missing source: {source}")
        elif reason:
            failures.append(f"protected source ({reason}): {source}")
        elif descendant_reason:
            failures.append(f"protected source ({descendant_reason}): {source}")
        elif destination.exists() or destination.is_symlink():
            failures.append(f"destination already exists: {destination}")
        elif not is_within(destination, allowed_root):
            failures.append(f"destination outside allowed root: {destination}")
        else:
            existing_parent = nearest_existing_parent(destination.parent)
            if not existing_parent.exists():
                failures.append(f"no existing destination ancestor: {destination}")
            elif source.stat().st_dev != existing_parent.stat().st_dev:
                failures.append(f"cross-volume move refused; use archive-copy: {source}")
        prepared.append((row, source, destination))
    if failures:
        raise SystemExit("Preflight failed:\n- " + "\n- ".join(failures))

    journal = absolute_path(args.journal) if args.journal else plan_path.parent / "journal.jsonl"
    rollback = absolute_path(args.rollback) if args.rollback else plan_path.parent / "rollback.csv"
    rollback_rows: list[dict[str, str]] = []
    for row, source, destination in prepared:
        append_journal(
            journal,
            {
                "event": "start",
                "action_id": row["action_id"],
                "batch": args.batch,
                "source": str(source),
                "destination": str(destination),
            },
        )
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.rename(source, destination)
        except Exception as exc:
            append_journal(
                journal,
                {"event": "failed", "action_id": row["action_id"], "error": str(exc)},
            )
            raise
        append_journal(journal, {"event": "complete", "action_id": row["action_id"]})
        rollback_rows.append(
            {
                "action_id": f"R-{row['action_id']}",
                "batch": f"rollback-{args.batch}",
                "action": "rename",
                "source": str(destination),
                "destination": str(source),
                "reason": f"inverse of {row['action_id']}",
                "confidence": "high",
                "decision": "pending",
            }
        )
    with rollback.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ACTION_FIELDS)
        writer.writeheader()
        writer.writerows(rollback_rows)
    print(journal)
    return 0


def iter_regular_files(path: Path) -> Iterator[tuple[Path, Path]]:
    if path.is_file() and not path.is_symlink():
        yield path, Path(path.name)
        return
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        dirs[:] = [name for name in dirs if not (root_path / name).is_symlink()]
        for name in files:
            candidate = root_path / name
            if not candidate.is_symlink() and candidate.is_file():
                yield candidate, candidate.relative_to(path)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def filesystem_personality(path: Path) -> str:
    if sys.platform != "darwin":
        return "unknown"
    existing = nearest_existing_parent(path)
    try:
        df_result = subprocess.run(
            ["df", "-P", str(existing)],
            check=True,
            capture_output=True,
            text=True,
        )
        lines = [line for line in df_result.stdout.splitlines() if line.strip()]
        if len(lines) < 2:
            return "unknown"
        device = lines[-1].split()[0]
        result = subprocess.run(
            ["diskutil", "info", device],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    for line in result.stdout.splitlines():
        if "File System Personality:" in line:
            return line.split(":", 1)[1].strip().casefold()
    return "unknown"


def find_oversize_files(path: Path, limit: int = FAT32_MAX_FILE) -> list[Path]:
    return [candidate for candidate, _ in iter_regular_files(path) if candidate.stat().st_size > limit]


def find_first_symlink(path: Path) -> Path | None:
    if path.is_symlink():
        return path
    if not path.is_dir():
        return None
    for root, dirs, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        for name in dirs + files:
            candidate = root_path / name
            if candidate.is_symlink():
                return candidate
    return None


def archive_copy_command(args: argparse.Namespace) -> int:
    if not args.execute or args.approval_token != APPROVAL_TOKEN:
        raise SystemExit(f"Refusing archive copy without --execute --approval-token {APPROVAL_TOKEN}")
    source = absolute_path(args.source)
    destination = absolute_path(args.destination)
    if not source.exists() or source.is_symlink():
        raise SystemExit(f"Source must exist and cannot be a symlink: {source}")
    nested_symlink = find_first_symlink(source)
    if nested_symlink:
        raise SystemExit(f"Archive source contains a symbolic link and cannot be fully verified: {nested_symlink}")
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f"Destination already exists: {destination}")
    personality = filesystem_personality(destination.parent)
    if "fat32" in personality or personality in {"ms-dos", "msdos"}:
        oversize = find_oversize_files(source)
        if oversize:
            raise SystemExit(f"FAT32 destination cannot hold file larger than 4 GiB: {oversize[0]}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination, follow_symlinks=False)

    report = absolute_path(args.report) if args.report else default_run_dir() / "archive-verification.csv"
    report.parent.mkdir(parents=True, exist_ok=True)
    source_files = list(iter_regular_files(source))
    rows: list[dict[str, str | int]] = []
    mismatches = 0
    for source_file, relative in source_files:
        destination_file = destination / relative if source.is_dir() else destination
        source_hash = sha256_file(source_file)
        destination_hash = sha256_file(destination_file) if destination_file.exists() else ""
        verified = source_hash == destination_hash
        mismatches += 0 if verified else 1
        rows.append(
            {
                "relative_path": str(relative),
                "size_bytes": source_file.stat().st_size,
                "source_sha256": source_hash,
                "destination_sha256": destination_hash,
                "verified": str(verified).lower(),
                "source_retained": "true",
            }
        )
    fields = [
        "relative_path",
        "size_bytes",
        "source_sha256",
        "destination_sha256",
        "verified",
        "source_retained",
    ]
    with report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    if mismatches:
        raise SystemExit(f"Archive verification failed for {mismatches} file(s); source was retained")
    print(report)
    return 0


def cleanup_report_command(args: argparse.Namespace) -> int:
    inventory = absolute_path(args.inventory)
    records = read_inventory(inventory)
    files: list[tuple[Path, int]] = []
    candidates: list[dict[str, str | int]] = []
    for record in records:
        if record.get("record_type") != "item" or record.get("kind") != "file":
            continue
        if record.get("protected"):
            continue
        path = absolute_path(record["path"])
        size = int(record.get("size_bytes", 0))
        files.append((path, size))
        suffix = path.suffix.casefold()
        if size == 0:
            candidates.append(
                {"type": "empty-file", "path": str(path), "size_bytes": 0, "reason": "empty file", "confidence": "medium", "sha256_group": ""}
            )
        elif suffix in INSTALLER_SUFFIXES:
            candidates.append(
                {"type": "installer", "path": str(path), "size_bytes": size, "reason": "installer image; confirm software is installed", "confidence": "low", "sha256_group": ""}
            )
        elif suffix in ARCHIVE_SUFFIXES and (path.parent / path.stem).is_dir():
            candidates.append(
                {"type": "archive", "path": str(path), "size_bytes": size, "reason": "same-named directory exists; verify extraction", "confidence": "low", "sha256_group": ""}
            )

    if not args.skip_duplicates:
        by_size: defaultdict[int, list[Path]] = defaultdict(list)
        for path, size in files:
            if size > 0 and path.exists() and not path.is_symlink():
                by_size[size].append(path)
        max_hash_bytes = int(args.max_hash_size_gb * 1024**3)
        for size, paths in by_size.items():
            if len(paths) < 2:
                continue
            if max_hash_bytes and size > max_hash_bytes:
                for path in paths:
                    candidates.append(
                        {"type": "same-size", "path": str(path), "size_bytes": size, "reason": "same size as another file; hash skipped by limit", "confidence": "low", "sha256_group": ""}
                    )
                continue
            by_hash: defaultdict[str, list[Path]] = defaultdict(list)
            for path in paths:
                try:
                    by_hash[sha256_file(path)].append(path)
                except OSError:
                    continue
            for digest, duplicates in by_hash.items():
                if len(duplicates) > 1:
                    for path in duplicates:
                        candidates.append(
                            {"type": "exact-duplicate", "path": str(path), "size_bytes": size, "reason": "same size and SHA-256 as another file", "confidence": "high", "sha256_group": digest}
                        )

    output = absolute_path(args.output) if args.output else inventory.parent / "cleanup-candidates.csv"
    fields = ["type", "path", "size_bytes", "reason", "confidence", "sha256_group"]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(candidates)
    print(output)
    return 0


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    for forbidden in '/\\:*?"<>|':
        value = value.replace(forbidden, "-")
    return " ".join(value.split()).strip(" .-")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("inventory", help="Create a read-only source inventory")
    inventory.add_argument("--source", action="append", required=True, help="Source directory; repeat as needed")
    inventory.add_argument("--max-depth", type=int, default=2, choices=range(1, 101))
    inventory.add_argument("--output", help="New private run directory")
    inventory.set_defaults(func=inventory_command)

    plan = subparsers.add_parser("plan", help="Create a conservative review plan")
    plan.add_argument("--inventory", required=True)
    plan.add_argument("--destination-root", default="~/Arquivo")
    plan.add_argument("--output", help="Actions CSV path")
    plan.set_defaults(func=plan_command)

    apply_parser = subparsers.add_parser("apply", help="Apply an explicitly approved same-volume batch")
    apply_parser.add_argument("--plan", required=True)
    apply_parser.add_argument("--batch", required=True)
    apply_parser.add_argument("--allowed-root", default="~/Arquivo")
    apply_parser.add_argument("--journal")
    apply_parser.add_argument("--rollback", help="Rollback CSV output path")
    apply_parser.add_argument("--execute", action="store_true")
    apply_parser.set_defaults(func=apply_command)

    archive = subparsers.add_parser("archive-copy", help="Copy and SHA-256 verify while retaining source")
    archive.add_argument("--source", required=True)
    archive.add_argument("--destination", required=True)
    archive.add_argument("--report")
    archive.add_argument("--execute", action="store_true")
    archive.add_argument("--approval-token", default="")
    archive.set_defaults(func=archive_copy_command)

    cleanup = subparsers.add_parser("cleanup-report", help="Report candidates without deleting")
    cleanup.add_argument("--inventory", required=True)
    cleanup.add_argument("--output")
    cleanup.add_argument("--max-hash-size-gb", type=float, default=5.0)
    cleanup.add_argument(
        "--skip-duplicates",
        action="store_true",
        help="Do not open file content; useful for cloud-backed sources",
    )
    cleanup.set_defaults(func=cleanup_report_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
