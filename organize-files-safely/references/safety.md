# Safety contract

## Non-negotiable rules

- Never delete files, empty Trash, or provide an automated delete action.
- Never overwrite or merge an existing destination.
- Never follow or move a symbolic link.
- Never descend into protected bundles, DICOM trees, virtual machines, Git repositories, application packages, cloud placeholders, or hidden technical directories.
- Keep processing local. Do not upload filenames, hashes, inventories, screenshots, or file contents.
- Inspect content only when metadata is insufficient and the user approves that batch.
- Stop a batch on the first failed precondition or action. Preserve the journal and generate inverse actions for completed same-volume moves.

## Approval gates

Inventory and planning may run without an action confirmation because they do not alter source files. Before `apply`, show the exact batch and obtain explicit approval. Before `archive-copy`, show source, destination, expected size, filesystem compatibility, and the rule that the source remains in place.

## Cloud folders

Moving an item out of an iCloud, Dropbox, Google Drive, or OneDrive folder can change remote state. Detect cloud-backed roots where possible, label the impact, and require an explicit cloud-aware approval before execution.

## External storage

Prefer APFS for Mac-only archives and exFAT when Windows interoperability is required. Refuse files larger than 4 GiB on FAT32. Copy first, verify SHA-256, keep the source, and report the local copy separately.

Refuse an archive source containing symbolic links because a regular-file checksum report cannot prove the link target was preserved safely.

## Cleanup candidates

Limit reports to evidence-backed candidates: exact hash duplicates, empty items, installer images, and archives with a plausibly extracted sibling. Never recommend medical, legal, tax, research, or personal originals solely because they are old.
