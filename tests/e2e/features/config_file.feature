@e2e
Feature: The config file on disk
  One process writes the config and the next reads it. An in-process test can
  fake the filesystem; only this layer proves the real XDG paths are honoured.

  Scenario: Init writes a real file under XDG_CONFIG_HOME
    Given no config file exists
    When I run the CLI with `config init`
    Then the exit code is 0
    And the config file exists in the sandbox

  Scenario: Init does not clobber a config the user has edited
    Given a config file with a hand-edited marker
    When I run the CLI with `config init`
    Then the exit code is 0
    And the hand-edited marker is still in the config file

  Scenario: Show reports the resolved config on stdout
    Given no config file exists
    When I run the CLI with `--no-colour config show`
    Then the exit code is 0
    And stdout contains "Config file:"
