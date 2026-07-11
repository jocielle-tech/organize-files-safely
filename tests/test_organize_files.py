from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "organize-files-safely" / "scripts" / "organize_files.py"
SPEC = importlib.util.spec_from_file_location("organize_files", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def run_cli(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != expect:
        raise AssertionError(
            f"Expected {expect}, got {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


class OrganizeFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.source.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_inventory_is_source_read_only_and_unicode_safe(self) -> None:
        sample = self.source / "Relatório sintético 01.txt"
        sample.write_text("synthetic", encoding="utf-8")
        before = (sample.read_bytes(), sample.stat().st_mtime_ns)
        output = self.base / "run"

        run_cli("inventory", "--source", str(self.source), "--output", str(output))

        after = (sample.read_bytes(), sample.stat().st_mtime_ns)
        self.assertEqual(before, after)
        rows = [json.loads(line) for line in (output / "inventory.jsonl").read_text().splitlines()]
        self.assertTrue(any(row.get("name") == sample.name for row in rows))

    def test_plan_locks_protected_package(self) -> None:
        (self.source / "Synthetic.app").mkdir()
        output = self.base / "run"
        run_cli("inventory", "--source", str(self.source), "--output", str(output))
        run_cli("plan", "--inventory", str(output / "inventory.jsonl"))
        with (output / "actions.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        protected = next(row for row in rows if row["source"].endswith("Synthetic.app"))
        self.assertEqual(protected["action"], "keep")
        self.assertEqual(protected["decision"], "locked")

    def test_apply_requires_execute_and_generates_rollback(self) -> None:
        source_file = self.source / "draft.txt"
        source_file.write_text("synthetic", encoding="utf-8")
        destination_root = self.base / "Arquivo"
        destination_root.mkdir()
        destination = destination_root / "10 - Projetos ativos" / "draft.txt"
        plan = self.base / "actions.csv"
        with plan.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MODULE.ACTION_FIELDS)
            writer.writeheader()
            writer.writerow(
                {
                    "action_id": "A000001",
                    "batch": "synthetic-1",
                    "action": "move",
                    "source": source_file,
                    "destination": destination,
                    "reason": "synthetic test",
                    "confidence": "high",
                    "decision": "approved",
                }
            )

        run_cli("apply", "--plan", str(plan), "--batch", "synthetic-1", "--allowed-root", str(destination_root), expect=1)
        self.assertTrue(source_file.exists())
        run_cli("apply", "--plan", str(plan), "--batch", "synthetic-1", "--allowed-root", str(destination_root), "--execute")
        self.assertFalse(source_file.exists())
        self.assertEqual(destination.read_text(), "synthetic")
        rollback = self.base / "rollback.csv"
        self.assertTrue(rollback.exists())
        with rollback.open(newline="", encoding="utf-8") as handle:
            rollback_rows = list(csv.DictReader(handle))
        rollback_rows[0]["decision"] = "approved"
        with rollback.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MODULE.ACTION_FIELDS)
            writer.writeheader()
            writer.writerows(rollback_rows)
        run_cli(
            "apply",
            "--plan",
            str(rollback),
            "--batch",
            "rollback-synthetic-1",
            "--allowed-root",
            str(self.source),
            "--execute",
        )
        self.assertTrue(source_file.exists())
        self.assertFalse(destination.exists())

    def test_apply_refuses_collision(self) -> None:
        source_file = self.source / "draft.txt"
        source_file.write_text("source", encoding="utf-8")
        destination_root = self.base / "Arquivo"
        destination_root.mkdir()
        destination = destination_root / "draft.txt"
        destination.write_text("existing", encoding="utf-8")
        plan = self.base / "actions.csv"
        with plan.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MODULE.ACTION_FIELDS)
            writer.writeheader()
            writer.writerow(
                {
                    "action_id": "A000001",
                    "batch": "collision",
                    "action": "move",
                    "source": source_file,
                    "destination": destination,
                    "reason": "synthetic test",
                    "confidence": "high",
                    "decision": "approved",
                }
            )
        run_cli("apply", "--plan", str(plan), "--batch", "collision", "--allowed-root", str(destination_root), "--execute", expect=1)
        self.assertEqual(source_file.read_text(), "source")
        self.assertEqual(destination.read_text(), "existing")

    def test_apply_refuses_directory_with_symlink(self) -> None:
        source_directory = self.source / "project"
        source_directory.mkdir()
        (source_directory / "document.txt").write_text("synthetic", encoding="utf-8")
        (source_directory / "link.txt").symlink_to(source_directory / "document.txt")
        destination_root = self.base / "Arquivo"
        destination_root.mkdir()
        plan = self.base / "actions.csv"
        with plan.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MODULE.ACTION_FIELDS)
            writer.writeheader()
            writer.writerow(
                {
                    "action_id": "A000001",
                    "batch": "protected",
                    "action": "move",
                    "source": source_directory,
                    "destination": destination_root / "project",
                    "reason": "synthetic test",
                    "confidence": "high",
                    "decision": "approved",
                }
            )
        run_cli("apply", "--plan", str(plan), "--batch", "protected", "--allowed-root", str(destination_root), "--execute", expect=1)
        self.assertTrue(source_directory.exists())
        self.assertFalse((destination_root / "project").exists())

    def test_archive_copy_verifies_and_retains_source(self) -> None:
        source_file = self.source / "completed.txt"
        source_file.write_text("completed synthetic project", encoding="utf-8")
        destination = self.base / "external" / "completed.txt"
        report = self.base / "archive-verification.csv"
        run_cli(
            "archive-copy",
            "--source",
            str(source_file),
            "--destination",
            str(destination),
            "--report",
            str(report),
            "--execute",
            "--approval-token",
            MODULE.APPROVAL_TOKEN,
        )
        self.assertTrue(source_file.exists())
        self.assertEqual(source_file.read_bytes(), destination.read_bytes())
        self.assertIn("true", report.read_text())

    def test_archive_copy_refuses_nested_symlink(self) -> None:
        source_directory = self.source / "completed"
        source_directory.mkdir()
        document = source_directory / "document.txt"
        document.write_text("synthetic", encoding="utf-8")
        (source_directory / "shortcut.txt").symlink_to(document)
        destination = self.base / "external" / "completed"
        run_cli(
            "archive-copy",
            "--source",
            str(source_directory),
            "--destination",
            str(destination),
            "--execute",
            "--approval-token",
            MODULE.APPROVAL_TOKEN,
            expect=1,
        )
        self.assertFalse(destination.exists())
        self.assertTrue(document.exists())

    def test_cleanup_report_finds_exact_duplicates_empty_and_installer(self) -> None:
        (self.source / "one.txt").write_text("same", encoding="utf-8")
        (self.source / "two.txt").write_text("same", encoding="utf-8")
        (self.source / "empty.txt").touch()
        (self.source / "synthetic.dmg").write_bytes(b"installer")
        output = self.base / "run"
        run_cli("inventory", "--source", str(self.source), "--output", str(output))
        run_cli("cleanup-report", "--inventory", str(output / "inventory.jsonl"))
        report = (output / "cleanup-candidates.csv").read_text(encoding="utf-8")
        self.assertIn("exact-duplicate", report)
        self.assertIn("empty-file", report)
        self.assertIn("installer", report)

    def test_cleanup_report_can_skip_cloud_content_hashing(self) -> None:
        (self.source / "one.txt").write_text("same", encoding="utf-8")
        (self.source / "two.txt").write_text("same", encoding="utf-8")
        (self.source / "empty.txt").touch()
        output = self.base / "run"
        run_cli("inventory", "--source", str(self.source), "--output", str(output))
        run_cli(
            "cleanup-report",
            "--inventory",
            str(output / "inventory.jsonl"),
            "--skip-duplicates",
        )
        report = (output / "cleanup-candidates.csv").read_text(encoding="utf-8")
        self.assertIn("empty-file", report)
        self.assertNotIn("exact-duplicate", report)

    def test_fat32_limit_helper(self) -> None:
        marker = self.source / "large.bin"
        with marker.open("wb") as handle:
            handle.truncate(MODULE.FAT32_MAX_FILE + 1)
        self.assertEqual(MODULE.find_oversize_files(self.source), [marker])

    @patch.object(MODULE.subprocess, "run")
    def test_filesystem_personality_uses_device_from_df(self, run_mock) -> None:
        run_mock.side_effect = [
            subprocess.CompletedProcess(
                ["df"],
                0,
                "Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/disk6s2 1 1 1 50% /Volumes/External\n",
                "",
            ),
            subprocess.CompletedProcess(
                ["diskutil"],
                0,
                "File System Personality:   MS-DOS FAT32\n",
                "",
            ),
        ]
        self.assertEqual(MODULE.filesystem_personality(Path("/tmp/example")), "ms-dos fat32")
        self.assertEqual(run_mock.call_args_list[1].args[0], ["diskutil", "info", "/dev/disk6s2"])

    def test_normalized_name_removes_forbidden_characters(self) -> None:
        self.assertEqual(MODULE.normalized_name('  Aula: revisão?  '), "Aula- revisão")


if __name__ == "__main__":
    unittest.main()
