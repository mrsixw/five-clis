"""Bind every scenario under ``features/``.

``scenarios()`` walks directories recursively, so one module covers every
feature file. The ``@e2e`` tag that keeps these out of ``make test`` is declared
in the feature files themselves — see ``docs/testing.md``.
"""

from pytest_bdd import scenarios

scenarios("features")
