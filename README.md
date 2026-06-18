# 🍔 five-clis

[![CI](https://github.com/mrsixw/five-clis/actions/workflows/ci.yml/badge.svg)](https://github.com/mrsixw/five-clis/actions/workflows/ci.yml)

**A batteries-included Python CLI template.** Named after Five Guys — burgers, shakes & fries → five CLI essentials.

Click **Use this template** to scaffold a new project with everything wired up and working from day one.

## What's included

| Essential | Description |
| --------- | ----------- |
| **Click** | Fully-wired entrypoint with `--version`, `--help`, `--completion` |
| **Shell completions** | bash, zsh, fish — generated and validated in CI |
| **Config file** | TOML config with XDG paths, `--init-config`, `--show-config` |
| **Themes** | `default`, `dark`, `light`, `mono`, `rainbow` — plus the full seasonal colour system |
| **Seasonal colours** | Date-driven ANSI palettes: western, jewish, islamic, hindu, sikh, east-asian |
| **Caching** | Generic TTL disk cache with atomic writes |
| **Auto-update** | GitHub release update checker with 24h cache |
| **Logging** | File logging to XDG state dir |
| **CI** | GitHub Actions: test, lint, build, spell, docs-lint, man, completions, release |
| **Release pipeline** | `git-mkver` version bumping, shiv binary, man page, `gh release create` |
| **install.sh** | One-liner install with binary + man page + shell completions |

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/mrsixw/five-clis/main/install.sh | bash
```

## Quick start

```bash
five-clis --help
five-clis --theme rainbow
five-clis --name Alice
five-clis --init-config
five-clis --show-config
eval "$(five-clis --completion bash)"
```

## Using this template

1. Click **Use this template** on GitHub
2. Clone your new repo
3. Replace occurrences of `fiveclis` / `five-clis` with your app name
4. Replace the `greet` business logic in `src/fiveclis/cli.py` with your own
5. Update `updater.py`: set `_UPDATE_CHECK_REPO` to your repo
6. Update `pyproject.toml`: set `name`, `description`, `scripts` entry point
7. Run `make test` to verify everything works

## Development

```bash
uv sync --extra dev
make format && make lint && make test
```

## Documentation

- [Options reference](docs/manual/options.md)
- [Usage guide](docs/manual/usage.md)
- [Troubleshooting](docs/manual/troubleshooting.md)
- [Contributing](CONTRIBUTING.md)
