# Organize Files Safely

[Português](README.pt-BR.md)

[![Agent Skills compatible](https://img.shields.io/badge/Agent%20Skills-compatible-4c1.svg)](https://agentskills.io)
![macOS first](https://img.shields.io/badge/runtime-macOS%20first-000000.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An open, macOS-first Agent Skill for inventorying, organizing, renaming, and archiving personal files with explicit approval gates. The same canonical skill works with **OpenAI Codex, Claude Code, Hermes Agent, and OpenClaw**. It never deletes files, never overwrites a destination, and keeps real inventories outside Git.

## Agent compatibility

The project follows the open [`SKILL.md` Agent Skills format](https://agentskills.io/specification). Compatibility claims are evidence-based and tracked at two levels: **installation verified** means the agent discovered the installed skill; **workflow verified** means the agent completed the synthetic read-only smoke test and produced the expected safety gates.

| Agent | Tested version | Installation | Workflow | Explicit invocation |
| --- | --- | --- | --- | --- |
| [OpenAI Codex](https://learn.chatgpt.com/docs/build-skills) | 0.144.2 | Verified on macOS | Verified on macOS | `$organize-files-safely` |
| [Claude Code](https://code.claude.com/docs/en/slash-commands) | 2.1.207 | Pending: login required | Pending: login required | `/organize-files-safely` |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/work-with-skills.md) | 0.18.2 | Verified on macOS | Pending: provider required | `/organize-files-safely` |
| [OpenClaw](https://github.com/openclaw/openclaw/blob/main/docs/tools/skills.md) | 2026.7.1 | Verified on macOS | Pending: provider required | `/organize-files-safely` |

Status snapshot: 2026-07-13. Pending agents are documented but are not advertised as workflow verified.

| Operating system | Status |
| --- | --- |
| macOS | Core CLI and Codex workflow tested; see per-agent status above |
| Linux | Not claimed in v1.1.0 |
| Windows | Not claimed in v1.1.0 |

ChatGPT skill packaging is a future compatibility target because local shell and bundled-script execution require separate validation.

## Real-world baseline

Privacy-reviewed Finder captures from the initial validation Mac. They show aggregate storage pressure without exposing filenames, personal documents, or private inventories.

<p align="center">
  <img src="docs/images/02-before-desktop-overview.png" alt="Aggregate iCloud Desktop size before organization" width="265">
  <img src="docs/images/04-before-storage-pressure.png" alt="APFS storage pressure before organization" width="265">
</p>

### Organized result

The local archive root uses numbered lifecycle categories so active projects, ongoing areas, references, records, and completed work remain easy to scan and migrate.

<p align="center">
  <img src="docs/images/05-after-organized-root.png" alt="Organized file root with seven lifecycle categories" width="720">
</p>

## Safety model

- Read-only inventory and conservative planning by default.
- Exact batch approval plus `--execute` for same-volume moves.
- Protected handling for symlinks, apps, bundles, DICOM, virtual machines, Git repositories, and cloud placeholders.
- Copy plus SHA-256 verification for external archives; the source remains in place.
- Cleanup reports only. There is no delete command.

## Install locally

Clone the repository once and keep the complete skill folder together:

```bash
git clone https://github.com/jocielle-tech/organize-files-safely.git
cd organize-files-safely
SKILL_SOURCE="$(pwd)/organize-files-safely"
```

The commands below intentionally fail if the destination already exists. Review the existing installation instead of overwriting it.

### OpenAI Codex

Codex now uses the shared Agent Skills directory. `~/.codex/skills` is a legacy location and is not the recommended installation path for new installs.

```bash
mkdir -p ~/.agents/skills
ln -s "$SKILL_SOURCE" ~/.agents/skills/organize-files-safely
test -f ~/.agents/skills/organize-files-safely/SKILL.md
```

Invoke with `$organize-files-safely` or ask Codex to use the skill by name.

### Claude Code

```bash
mkdir -p ~/.claude/skills
ln -s "$SKILL_SOURCE" ~/.claude/skills/organize-files-safely
test -f ~/.claude/skills/organize-files-safely/SKILL.md
```

Start a new Claude Code session and invoke `/organize-files-safely`.

### Hermes Agent

```bash
mkdir -p ~/.hermes/skills
cp -R "$SKILL_SOURCE" ~/.hermes/skills/organize-files-safely
hermes skills list | grep organize-files-safely
```

Start a new Hermes session and invoke `/organize-files-safely`.

### OpenClaw

OpenClaw can discover the same `~/.agents/skills` installation used by Codex. For an OpenClaw-managed global installation from the local clone, use:

```bash
openclaw skills install "$SKILL_SOURCE" --as organize-files-safely --global
openclaw skills list | grep organize-files-safely
```

Invoke `/organize-files-safely` or ask OpenClaw to use the skill by name.

Public repository: [jocielle-tech/organize-files-safely](https://github.com/jocielle-tech/organize-files-safely).

## First inventory

```bash
python3 "$SKILL_SOURCE/scripts/organize_files.py" inventory \
  --source ~/Downloads --max-depth 2
```

Private output is written to `~/.organize-files-safely/runs/`. Do not commit it.

Example request:

> Use organize-files-safely to inspect `~/Downloads` without changing anything.

Expected output:

```text
Inventory complete
Mode: read-only
Private run: ~/.organize-files-safely/runs/<run-id>/
Source modifications: 0
Next step: review the proposed actions
```

## Development

```bash
python3 -m unittest discover -s tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ./organize-files-safely
skills-ref validate ./organize-files-safely
```

## License

MIT. See [LICENSE](LICENSE).
