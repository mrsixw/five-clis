#!/usr/bin/env bats
#
# 🍔 install.sh — the published `curl | bash` install path.
#
# install.sh ships mode 644 and is documented as `curl ... | bash`, so the tests
# drive it through `bash` exactly as a user would.
#
# HOME is redirected into the test's temporary directory, so every path the
# installer writes to lands there and nothing touches the developer's machine.

setup() {
  load 'helpers/common'
  common_setup

  # curl serves the binary, the man page and the completions. Unlike some
  # siblings, this installer queries no release API: everything comes from
  # /releases/latest/download.
  stub curl <<'STUB'
url=""; out=""; prev=""
for arg in "$@"; do
  [[ "${prev}" == "-o" ]] && out="${arg}"
  [[ "${arg}" == http* ]] && url="${arg}"
  prev="${arg}"
done

case "${url}" in
  *.1.gz)
    [[ -n "${MAN_FAILS:-}" ]] && exit 22
    printf 'man page\n' > "${out}"; exit 0 ;;
  *.bash|*.fish|*/_*)
    [[ -n "${COMPLETIONS_FAIL:-}" ]] && exit 22
    printf 'completion\n' > "${out}"; exit 0 ;;
  *)
    [[ -n "${BINARY_FAILS:-}" ]] && exit 22
    # A stand-in for the real zipapp: it answers --version, and records how it
    # was invoked so the tests can prove which config command was used.
    {
      printf '#!/usr/bin/env bash\n'
      printf 'printf "%%s\\n" "$*" >> "%s/binary.log"\n' "${STUB_LOG}"
      printf 'if [[ "$1" == "config" && -n "${BINARY_LACKS_CONFIG_CMD:-}" ]]; then exit 2; fi\n'
      printf 'if [[ "$1" == "--version" ]]; then printf "%%s, version 1.2.3\\n" "%s"; fi\n' "${BINARY_NAME}"
      printf 'exit 0\n'
    } > "${out}"
    exit 0 ;;
esac
STUB
}

binary_calls() { cat "${STUB_LOG}/binary.log" 2>/dev/null || true; }

@test "installs the binary, executable, under ~/.local/bin" {
  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  [ -x "${FAKE_HOME}/.local/bin/${BINARY_NAME}" ]
}

@test "downloads from the latest-release directory" {
  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_called curl "/releases/latest/download/${BINARY_NAME}"
}

@test "reports the installed version" {
  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_output_contains "version 1.2.3"
}

@test "seeds a default config with the modern subcommand" {
  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  printf '%s\n' "$(binary_calls)" | grep -qx "config init"
}

@test "falls back to --init-config for a pre-0.3 binary" {
  # The fallback exists because older releases have no `config` subcommand.
  # Without a test, nothing notices when it stops working.
  export BINARY_LACKS_CONFIG_CMD=1

  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  printf '%s\n' "$(binary_calls)" | grep -qx -- "--init-config"
}

@test "installs the man page and all three completions" {
  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  [ -f "${FAKE_HOME}/.local/share/man/man1/${BINARY_NAME}.1.gz" ]
  [ -f "${FAKE_HOME}/.local/share/bash-completion/completions/${BINARY_NAME}" ]
  [ -f "${FAKE_HOME}/.local/share/zsh/site-functions/_${BINARY_NAME}" ]
  [ -f "${FAKE_HOME}/.config/fish/completions/${BINARY_NAME}.fish" ]
}

@test "fails when the binary download fails" {
  export BINARY_FAILS=1

  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 1 ]
  assert_output_contains "Failed to download binary"
  [ ! -e "${FAKE_HOME}/.local/bin/${BINARY_NAME}" ]
}

@test "treats a missing man page as non-fatal" {
  # The binary is installed by this point; refusing to finish over a man page
  # would leave the user worse off than a warning does.
  export MAN_FAILS=1

  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_output_contains "Could not install man page"
  [ -x "${FAKE_HOME}/.local/bin/${BINARY_NAME}" ]
}

@test "treats missing completions as non-fatal" {
  export COMPLETIONS_FAIL=1

  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_output_contains "Could not install bash completion"
  assert_output_contains "Could not install zsh completion"
  assert_output_contains "Could not install fish completion"
}

@test "prints zsh instructions to a zsh user" {
  SHELL=/bin/zsh run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_output_contains "Add this to your ~/.zshrc"
  assert_output_contains "fpath="
  # Not "~/.bashrc": the PATH warning below names both files, so a loose
  # assertion here would pass whichever branch ran.
  refute_output_contains "~/.bashrc:"
}

@test "prints bash instructions to a bash user" {
  SHELL=/bin/bash run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_output_contains "Add this to your ~/.bashrc:"
  refute_output_contains "compinit"
}

@test "tells a fish user there is nothing to do" {
  SHELL=/usr/bin/fish run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_output_contains "Nothing to do"
}

@test "falls back to all three when the shell is unrecognised" {
  SHELL=/bin/ksh run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  # The catch-all branch names all three shells in its own distinctive form.
  assert_output_contains "bash — add to"
  assert_output_contains "zsh  — add to"
  assert_output_contains "fish — nothing to do"
}

@test "warns when the install directory is not on PATH" {
  run bash "${REPO_ROOT}/install.sh"

  [ "$status" -eq 0 ]
  assert_output_contains "is not in your PATH"
}

@test "stays quiet about PATH when the install directory is already on it" {
  PATH="${FAKE_HOME}/.local/bin:${PATH}" run bash "${REPO_ROOT}/install.sh"

  # Assert the run succeeded first: a refute on its own also passes when the
  # script never started.
  [ "$status" -eq 0 ]
  refute_output_contains "is not in your PATH"
}
