# Organize Files Safely

[English](README.md)

[![Compatível com Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-4c1.svg)](https://agentskills.io)
![macOS inicialmente](https://img.shields.io/badge/runtime-macOS%20first-000000.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)
[![Licença MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Uma Agent Skill aberta, inicialmente para macOS, que inventaria, organiza, renomeia e arquiva arquivos pessoais com aprovações explícitas. A mesma skill canônica funciona com **OpenAI Codex, Claude Code, Hermes Agent e OpenClaw**. Ela não apaga arquivos, não sobrescreve destinos e mantém inventários reais fora do Git.

## Compatibilidade com agentes

O projeto segue o formato aberto [`SKILL.md` do Agent Skills](https://agentskills.io/specification). As declarações de compatibilidade são baseadas em evidências e registradas em dois níveis: **instalação verificada** significa que o agente encontrou a skill; **workflow verificado** significa que o agente concluiu o teste sintético somente leitura e apresentou as barreiras de segurança esperadas.

| Agente | Versão testada | Instalação | Workflow | Invocação explícita |
| --- | --- | --- | --- | --- |
| [OpenAI Codex](https://learn.chatgpt.com/docs/build-skills) | 0.144.2 | Verificada no macOS | Verificado no macOS | `$organize-files-safely` |
| [Claude Code](https://code.claude.com/docs/en/slash-commands) | 2.1.207 | Pendente: requer login | Pendente: requer login | `/organize-files-safely` |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/work-with-skills.md) | 0.18.2 | Verificada no macOS | Pendente: requer provedor | `/organize-files-safely` |
| [OpenClaw](https://github.com/openclaw/openclaw/blob/main/docs/tools/skills.md) | 2026.7.1 | Verificada no macOS | Pendente: requer provedor | `/organize-files-safely` |

Registro de estado: 2026-07-13. Os agentes pendentes estão documentados, mas não são divulgados como workflow verificado.

| Sistema operacional | Estado |
| --- | --- |
| macOS | CLI principal e workflow do Codex testados; consulte o estado por agente acima |
| Linux | Não declarado na v1.1.0 |
| Windows | Não declarado na v1.1.0 |

O empacotamento como skill do ChatGPT permanece como compatibilidade futura, pois o acesso ao shell local e a execução dos scripts incluídos exigem validação separada.

## Cenário real antes da organização

Capturas do Finder revisadas para privacidade, obtidas no Mac usado na validação inicial. Elas mostram apenas métricas agregadas de armazenamento, sem nomes de arquivos, documentos pessoais ou inventários privados.

<p align="center">
  <img src="docs/images/02-before-desktop-overview.png" alt="Tamanho agregado da Mesa no iCloud antes da organização" width="265">
  <img src="docs/images/04-before-storage-pressure.png" alt="Pressão de armazenamento APFS antes da organização" width="265">
</p>

### Resultado organizado

A raiz local usa categorias numeradas por ciclo de vida, facilitando a visualização e a futura migração de projetos ativos, áreas contínuas, referências, registros e trabalhos concluídos.

<p align="center">
  <img src="docs/images/05-after-organized-root.png" alt="Raiz organizada com sete categorias por ciclo de vida" width="720">
</p>

## Modelo de segurança

- Inventário somente leitura e planejamento conservador por padrão.
- Aprovação do lote exato e `--execute` para movimentações no mesmo volume.
- Proteção para links, aplicativos, pacotes, DICOM, máquinas virtuais, repositórios Git e placeholders de nuvem.
- Cópia e verificação SHA-256 para arquivos externos, mantendo a origem.
- Apenas relatórios de candidatos à limpeza; não existe comando de exclusão.

## Instalação local

Clone o repositório uma vez e mantenha completa a pasta da skill:

```bash
git clone https://github.com/jocielle-tech/organize-files-safely.git
cd organize-files-safely
SKILL_SOURCE="$(pwd)/organize-files-safely"
```

Os comandos abaixo falham intencionalmente quando o destino já existe. Revise a instalação existente em vez de sobrescrevê-la.

### OpenAI Codex

O Codex atualmente usa a pasta compartilhada do padrão Agent Skills. `~/.codex/skills` é um caminho legado e não é a instalação recomendada para novos usuários.

```bash
mkdir -p ~/.agents/skills
ln -s "$SKILL_SOURCE" ~/.agents/skills/organize-files-safely
test -f ~/.agents/skills/organize-files-safely/SKILL.md
```

Invoque com `$organize-files-safely` ou peça ao Codex para usar a skill pelo nome.

### Claude Code

```bash
mkdir -p ~/.claude/skills
ln -s "$SKILL_SOURCE" ~/.claude/skills/organize-files-safely
test -f ~/.claude/skills/organize-files-safely/SKILL.md
```

Inicie uma nova sessão do Claude Code e invoque `/organize-files-safely`.

### Hermes Agent

```bash
mkdir -p ~/.hermes/skills
cp -R "$SKILL_SOURCE" ~/.hermes/skills/organize-files-safely
hermes skills list | grep organize-files-safely
```

Inicie uma nova sessão do Hermes e invoque `/organize-files-safely`.

### OpenClaw

O OpenClaw pode encontrar a mesma instalação em `~/.agents/skills` usada pelo Codex. Para uma instalação global gerenciada pelo OpenClaw a partir do clone local, use:

```bash
openclaw skills install "$SKILL_SOURCE" --as organize-files-safely --global
openclaw skills list | grep organize-files-safely
```

Invoque `/organize-files-safely` ou peça ao OpenClaw para usar a skill pelo nome.

Repositório público: [jocielle-tech/organize-files-safely](https://github.com/jocielle-tech/organize-files-safely).

## Primeiro inventário

```bash
python3 "$SKILL_SOURCE/scripts/organize_files.py" inventory \
  --source ~/Downloads --max-depth 2
```

Os dados privados ficam em `~/.organize-files-safely/runs/` e nunca devem ser versionados.

Exemplo de solicitação:

> Use organize-files-safely para inspecionar `~/Downloads` sem alterar nada.

Output esperado:

```text
Inventory complete
Mode: read-only
Private run: ~/.organize-files-safely/runs/<run-id>/
Source modifications: 0
Next step: review the proposed actions
```

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ./organize-files-safely
skills-ref validate ./organize-files-safely
```

## Licença

MIT. Consulte [LICENSE](LICENSE).
