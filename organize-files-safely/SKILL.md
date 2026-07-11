---
name: organize-files-safely
description: Safely inventory, classify, rename, organize, and archive personal files with explicit approval gates, collision protection, audit journals, rollback plans, duplicate reports, and copy verification. Use when Codex needs to organize macOS folders such as Desktop or Downloads, propose a folder taxonomy, prepare completed projects for external storage, standardize filenames, identify cleanup candidates without deleting them, or execute an already approved batch of file moves.
---

# Organize Files Safely

Organize user files through a reviewable, local-only workflow. Never delete files or infer approval from a general organization request.

## Workflow

1. Read [safety.md](references/safety.md) before touching real files.
2. Inventory the requested sources. Default to a shallow first pass and keep the run outside the project repository.
3. Generate a conservative plan. Treat ambiguous items as `review`; never invent dates, categories, or completed-project status.
4. Present actions in small batches with source, destination, reason, confidence, conflicts, and cloud impact.
5. Apply only the exact batch the user explicitly approves. Keep the plan and journal for rollback.
6. Copy completed projects to compatible external storage and verify SHA-256. Keep the source and report it as a possible local cleanup candidate.
7. Report cleanup candidates; never delete or move them to Trash.

## Commands

Use `python3 scripts/organize_files.py --help` for all options.

```bash
python3 scripts/organize_files.py inventory \
  --source ~/Downloads --max-depth 2

python3 scripts/organize_files.py plan \
  --inventory ~/.organize-files-safely/runs/<run-id>/inventory.jsonl \
  --destination-root ~/Arquivo

python3 scripts/organize_files.py cleanup-report \
  --inventory ~/.organize-files-safely/runs/<run-id>/inventory.jsonl
```

Add `--skip-duplicates` for iCloud or other cloud-backed sources so the report never opens content or triggers downloads.

`apply` and `archive-copy` are mutating commands. Run them only after showing the final batch and receiving action-time approval. They require explicit execution flags and still refuse unsafe operations.

## Decision Rules

- Use [taxonomy.md](references/taxonomy.md) to propose destinations.
- Use [naming.md](references/naming.md) to propose names.
- Preserve apps, bundles, DICOM trees, virtual machines, Git repositories, cloud placeholders, symlinks, and hidden technical content as protected units.
- Treat Desktop and Documents as cloud-impacting when macOS reports iCloud synchronization.
- Mark inactivity only as a review signal. Let the user decide whether a project is complete.
- Never overwrite, merge automatically, append arbitrary collision suffixes, reformat a disk, or remove a verified source copy.
- Keep real inventories, screenshots, hashes, and journals outside Git. Use synthetic fixtures in public materials.

## Outputs

Store private runs under `~/.organize-files-safely/runs/<run-id>/`. The command suite may produce `inventory.jsonl`, `inventory-summary.json`, `actions.csv`, `review.md`, `journal.jsonl`, `rollback.csv`, `archive-verification.csv`, and `cleanup-candidates.csv`.
