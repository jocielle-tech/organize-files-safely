# Naming policy

Use a conservative, human-readable pattern:

`YYYY-MM-DD - Subject - Description - vNN.ext`

- Include only trusted components. Omit an unknown date, subject, description, or version.
- Do not treat filesystem creation or modification time as the document date.
- Use `YYYY - Project name` for project folders when the year is known.
- Preserve the extension and meaningful original wording.
- Normalize repeated whitespace and remove characters incompatible with common filesystems: `/`, `\\`, `:`, `*`, `?`, `\"`, `<`, `>`, and `|`.
- Preserve Unicode letters while normalizing names to NFC.
- Do not replace a collision with `copy`, `final-final`, or a numeric suffix automatically. Send it to review.
- Do not rename internal files in protected packages or technical trees.
