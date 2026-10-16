@e2e
Feature: CLI contract
  The built binary must honour its documented exit codes and keep data on
  stdout separate from progress and errors on stderr. CliRunner merges the two
  streams, so this is the only layer that can prove the split.

  Scenario: Version matches the VERSION file
    When I run the CLI with `--version`
    Then the exit code is 0
    And stdout reports the version from the VERSION file
    And stderr is empty

  Scenario: Help lists the subcommands
    When I run the CLI with `--help`
    Then the exit code is 0
    And stdout names the binary
    And stdout contains "completions"
    And stdout contains "config"
    And stdout contains "greet"

  Scenario: An unknown option is a usage error on stderr
    When I run the CLI with `--definitely-not-an-option`
    Then the exit code is 2
    And stdout is empty
    And stderr contains "Error"

  Scenario: An unknown subcommand is a usage error on stderr
    When I run the CLI with `definitely-not-a-command`
    Then the exit code is 2
    And stdout is empty
    And stderr contains "No such command"

  Scenario: An invalid theme is rejected before anything is printed
    When I run the CLI with `--theme definitely-not-a-theme`
    Then the exit code is 2
    And stdout is empty
    And stderr contains "Invalid value"

  Scenario: Progress goes to stderr and data goes to stdout
    When I run the CLI with `--no-colour greet --name Ada`
    Then the exit code is 0
    And stdout contains "Hello, Ada!"
    And stdout does not contain "Cooking up"
    And stderr contains "Cooking up"

  Scenario: No-colour output really carries no escapes
    When I run the CLI with `--no-colour greet --name Ada`
    Then the exit code is 0
    And stdout carries no ANSI colour

  Scenario Outline: Completion scripts are evaluable by <shell>
    When I run the CLI with `completions <shell>`
    Then the exit code is 0
    And the completion script is evaluable by <shell>

    Examples:
      | shell |
      | bash  |
      | zsh   |
      | fish  |
