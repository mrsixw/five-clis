# Usage Guide

## Basic usage

```bash
five-clis                       # same as: five-clis greet
five-clis greet --name Alice
five-clis --theme rainbow
five-clis --no-colour
```

Global options (`--theme`, `--no-colour`, `--config`, …) go before the
subcommand; they are resolved once and shared with every command.

## Themes

```bash
five-clis --theme default
five-clis --theme dark
five-clis --theme light
five-clis --theme mono       # no colour
five-clis --theme rainbow    # cycling ROYGBIV
```

## Seasonal colours

Seasonal colours are on by default. They change automatically around holidays:

```bash
five-clis                                  # western calendar (default)
five-clis --seasonal-calendar jewish       # Hanukkah, Passover, etc.
five-clis --no-seasonal-colours            # disable entirely
```

## Config file

```bash
five-clis config init               # write ~/.config/fiveclis/config.toml
five-clis config show               # print resolved config
five-clis --config my.toml greet    # use a custom config file
```

## Shell completions

```bash
eval "$(five-clis completions bash)"   # bash
eval "$(five-clis completions zsh)"    # zsh
five-clis completions fish | source    # fish
```

`install.sh` installs these permanently and prints the one line your shell
needs to load them. Dropping the files into place is not enough on its own:
zsh wants the directory on `fpath` above `compinit`, and bash wants either the
`bash-completion` package or an explicit `source`. Only fish needs nothing.

## Updating

```bash
five-clis update                       # fetch and install the latest release
```

Replaces the running executable in place, atomically — an interrupted download
leaves the working binary untouched. Re-run `install.sh` if you also want a
refreshed man page.

## Caching

```bash
five-clis --cache                      # enable caching
five-clis --cache --cache-ttl 10m      # cache for 10 minutes
five-clis --no-cache                   # disable caching
```
