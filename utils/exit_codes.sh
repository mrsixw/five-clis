#!/usr/bin/env bash
# Exit codes shared by the release scripts and the CI steps that run them.
# Source this file; both sides read the same names.

# shellcheck disable=SC2034  # Read by the scripts and workflow steps that source this.
readonly EXIT_FAILURE=1
# The branch gained a newer commit while this run was releasing. The run for
# that commit releases everything this one would have, so this one stops.
# shellcheck disable=SC2034
readonly EXIT_SUPERSEDED=3
