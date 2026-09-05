.ONESHELL:
SHELL = /bin/bash

# Pinned to the version the CI spell job uses. Floating it would reintroduce
# exactly the drift this target exists to remove.
TYPOS_VERSION := 1.48.0

# Every shell source we ship, plus the test helper, which is shell too and just
# as capable of being wrong.
SHELL_SOURCES := install.sh $(wildcard utils/*.sh) tests/bats/helpers/common.bash

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
DESTDIR ?=

.PHONY: build release test e2e bats lint docs-lint shellcheck spell format man completions install uninstall

.venv:
	uv venv .venv
	uv sync --extra dev

build: .venv
	uv sync --extra build
	mkdir -p dist
	uv run shiv -c five-clis -o dist/five-clis --python '/usr/bin/env python3' --preamble utils/preamble.py .

install: build
	install -d "$(DESTDIR)$(BINDIR)"
	install -m 755 dist/five-clis "$(DESTDIR)$(BINDIR)/five-clis"

uninstall:
	rm -f "$(DESTDIR)$(BINDIR)/five-clis"

release: build

test: .venv
	uv sync --extra test
	uv run pytest -v

lint: .venv docs-lint shellcheck spell
	uv sync --extra lint
	uv run ruff check .
	uv run black --check .

docs-lint:
	npx --yes markdownlint-cli2 "docs/**/*.md" "README.md" "CONTRIBUTING.md"

# Static analysis for every shell source.
shellcheck:
	npx --yes shellcheck $(SHELL_SOURCES)

# The shell test suite. bats and shellcheck arrive via npx, exactly as
# markdownlint-cli2 does above — nothing to install by hand.
bats:
	npx --yes bats tests/bats

# Spelling, the same check CI runs. uvx fetches typos on demand; uv is already
# this project's package manager.
spell:
	uvx --from typos==$(TYPOS_VERSION) typos

format: .venv
	uv sync --extra lint
	uv run ruff check --fix .
	uv run black .

man: .venv
	uv sync --extra build
	mkdir -p man1
	uv run python utils/generate_man_page.py man1
	gzip -f man1/five-clis.1

completions: .venv
	uv sync
	mkdir -p completions
	_FIVE_CLIS_COMPLETE=bash_source uv run five-clis > completions/five-clis.bash
	sed -i.bak 's/_FIVE_CLIS_COMPLETE=bash_complete $$1)/_FIVE_CLIS_COMPLETE=bash_complete "$$1")/' completions/five-clis.bash
	sed -i.bak 's/COMPREPLY+=($$value)/COMPREPLY+=("$$value")/' completions/five-clis.bash
	rm -f completions/five-clis.bash.bak
	_FIVE_CLIS_COMPLETE=zsh_source uv run five-clis > completions/_five-clis
	_FIVE_CLIS_COMPLETE=fish_source uv run five-clis > completions/five-clis.fish
