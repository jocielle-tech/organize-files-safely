# Organize Files Safely

[English](README.md)

Uma skill Codex, inicialmente para macOS, que inventaria, organiza, renomeia e arquiva arquivos pessoais com aprovações explícitas. Ela não apaga arquivos, não sobrescreve destinos e mantém inventários reais fora do Git.

## Modelo de segurança

- Inventário somente leitura e planejamento conservador por padrão.
- Aprovação do lote exato e `--execute` para movimentações no mesmo volume.
- Proteção para links, aplicativos, pacotes, DICOM, máquinas virtuais, repositórios Git e placeholders de nuvem.
- Cópia e verificação SHA-256 para arquivos externos, mantendo a origem.
- Apenas relatórios de candidatos à limpeza; não existe comando de exclusão.

## Instalação local

```bash
git clone https://github.com/jocielle-tech/organize-files-safely.git
ln -s "$(pwd)/organize-files-safely" ~/.codex/skills/organize-files-safely
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ~/.codex/skills/organize-files-safely
```

O endereço do repositório somente ficará disponível depois da validação e da aprovação para publicação.

## Primeiro inventário

```bash
python3 organize-files-safely/scripts/organize_files.py inventory \
  --source ~/Downloads --max-depth 2
```

Os dados privados ficam em `~/.organize-files-safely/runs/` e nunca devem ser versionados.

## Desenvolvimento

```bash
python3 -m unittest discover -s tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  ./organize-files-safely
```

## Licença

MIT. Consulte [LICENSE](LICENSE).
