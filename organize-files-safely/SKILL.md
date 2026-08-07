---
name: organize-files-safely
description: Safely inventory, classify, rename, organize, and archive personal files with explicit approval gates, collision protection, audit journals, rollback plans, duplicate reports, and copy verification. Use when an AI agent needs to organize macOS folders such as Desktop or Downloads, propose a folder taxonomy, prepare completed projects for external storage, standardize filenames, identify cleanup candidates without deleting them, or execute an already approved batch of file moves.
---

# Organize Files Safely

Organize user files through a reviewable, local-only workflow. Never delete files or infer approval from a general organization request.

## Runtime compatibility

Use this canonical skill folder unchanged with Agent Skills-compatible agents, including OpenAI Codex, Claude Code, Hermes Agent, and OpenClaw. Resolve the skill root as the directory containing this `SKILL.md` before running bundled scripts; never assume the current working directory is the skill root.

Use `python3 "<skill-root>/scripts/organize_files.py" --help` to confirm the resolved path. Treat `agents/openai.yaml` as optional Codex interface metadata, not as a runtime requirement. Do not depend on agent-specific frontmatter or tools for the safety workflow.

## Quick tutorial

Use the skill by naming a source and the desired outcome. Keep the default workflow when the user does not request customization.

### 1. Inventory without changes

Example request:

> Use `organize-files-safely` to inspect `~/Downloads` without changing anything.

Expected output:

```text
Inventory complete
Source: ~/Downloads
Mode: read-only
Private run: ~/.organize-files-safely/runs/<run-id>/
Source modifications: 0
Next step: review the proposed actions
```

### 2. Propose an organization plan

Example request:

> Organize my Downloads into small reviewable batches.

Expected output:

```text
Batch 001 — proposed, not executed
Items: 5
Destination: ~/Arquivo/00 - Entrada/...
Conflicts: 0
Cloud impact: none
Approval required before apply
```

### 3. Apply an approved batch

Example request:

> I approve batch 001 exactly as shown.

Expected output:

```text
Batch 001 complete
Completed actions: 5
Failed actions: 0
Journal: <private-run>/journal-batch-001.jsonl
Rollback: <private-run>/rollback-batch-001.csv
Deleted files: 0
```

### 4. Copy a completed project to external storage

Example request:

> Prepare this completed project for my external drive and keep the source.

Expected output before execution:

```text
Source and destination verified
Filesystem compatibility checked
Expected copy size reported
Source retention: required
Explicit approval required before copy and SHA-256 verification
```

### 5. Request a custom output folder

The user may request a specific private run folder or a specific destination folder. Honor the requested path only after checking scope, permissions, collisions, cloud impact, and filesystem compatibility. Do not change the default paths when the user does not request customization.

Example requests:

> Save this inventory in `~/.organize-files-safely/runs/my-audit`.

> Create `~/Arquivo/20 - Areas/Teaching` as the destination in the proposed plan.

Expected output:

```text
Requested output: <exact requested path>
Path status: available or conflict detected
Action status: proposed
Approval required before creating a destination or moving files
```

## Workflow

1. Read [safety.md](references/safety.md) before touching real files.
2. Inventory the requested sources. Default to a shallow first pass and keep the run outside the project repository.
3. Generate a conservative plan. Treat ambiguous items as `review`; never invent dates, categories, or completed-project status.
4. Present actions in small batches with source, destination, reason, confidence, conflicts, and cloud impact.
5. Apply only the exact batch the user explicitly approves. Keep the plan and journal for rollback.
6. Copy completed projects to compatible external storage and verify SHA-256. Keep the source and report it as a possible local cleanup candidate.
7. Report cleanup candidates; never delete or move them to Trash.

## Commands

Resolve `<skill-root>` to the directory containing this `SKILL.md`, then use `python3 "<skill-root>/scripts/organize_files.py" --help` for all options.

```bash
python3 "<skill-root>/scripts/organize_files.py" inventory \
  --source ~/Downloads --max-depth 2

python3 "<skill-root>/scripts/organize_files.py" plan \
  --inventory ~/.organize-files-safely/runs/<run-id>/inventory.jsonl \
  --destination-root ~/Arquivo

python3 "<skill-root>/scripts/organize_files.py" cleanup-report \
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
