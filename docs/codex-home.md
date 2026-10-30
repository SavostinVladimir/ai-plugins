# Common Codex installation root

## Requirement
Add --codex-home DIRECTORY to plan/install and all other lifecycle commands so users can keep all framework configuration in one mounted directory. This is an installer option, not a claim that any corporate harness discovers the folder automatically.

## Paths and compatibility
For an explicitly supplied common root ROOT: agents=ROOT/agents, skills=ROOT/skills, instructions=ROOT/AGENTS.override.md if it exists otherwise ROOT/AGENTS.md, native config=ROOT/config.toml, manager state=ROOT/.agent-frameworks/state/INSTANCE. Native config remains read-only/diagnostic. No files are written outside ROOT unless a per-component override is explicitly supplied. If no common root is supplied, preserve existing defaults and existing registry paths exactly (including HOME/.agents/skills). Existing environment CODEX_HOME behavior stays unchanged; this feature is an explicit installer shorthand.
Each per-component CLI flag wins over instance.paths; both override derived common-root defaults. CLI relative root resolves against cwd; home/env expansion and unresolved-variable rejection use existing path validation. Resolve root symlinks; reject roots that are files. Existing state binding/conflict logic (manager/engine.py: load_state and build_plan) remains; repeat the same root on update/status/uninstall/check. Plan remains read-only; do not silently fall back from read-only mounts.

## CUJ
A developer sees the mounted Codex folder inside a corporate sandbox. They run `python3 manage.py plan spec-review --codex-home /mounted/codex`, inspect actual paths below that folder, models and conflicts. Plan creates no files. They run install with the identical root and see completion and runtime-verification limitations. They later use the same argument for update/check/uninstall and receive the usual results. If plan or install detects a conflicting preexisting/modified file or managed block, the developer sees the concrete conflict and a nonzero exit code; existing config contents remain unchanged, and installation is not reported complete. The user can inspect backups and reconcile deliberately; no force is applied automatically. If the root is invalid or inaccessible, the CLI shows an error and does not substitute a personal directory.

## Acceptance
Tests cover common-root plan with no writes, install/check/update/uninstall entirely below root, AGENTS.override selection, unchanged no-flag defaults, CLI-root vs per-component precedence, relative CLI root, explicit component overrides and invalid roots. README contains matching plan/install examples and warns that client discovery still needs verification. Preserve all existing tests and native agent files.

## Evidence
Current implementation before this change: manager/configuration.py configure defines independent path defaults; manager/cli.py parser defines per-component flags. The common-root derivation above is new required behavior. Existing installation protocol is in docs/specification.md; this addendum takes precedence only for explicit common roots.

## Protection of existing configuration
User explicitly requires preventing damage to existing configs. config.toml is diagnostic only and must remain byte-for-byte unchanged. Preserve all unrelated AGENTS text, native file permissions, and existing conflict/adoption semantics. Differing foreign payloads or modified managed payloads/blocks cause a conflict before mutation. No implicit --adopt, --force, fallback path, or repair of user configs. Journals precede payload writes; an injected failure on instruction write must restore earlier payload changes. Shared-root invalid-file, protected-path collision, final-file symlink, native-config preservation, instruction preservation and rollback receive regression tests. Document --adopt's limited scope and backups; atomic per-file writes do not promise crash-proof multi-file transactions.

Safety evidence: manager/state.py atomic_write preserves existing mode; transaction records the recovery journal before payload writes and restores prior contents on failure. These are requirements to retain and cover with regression tests.
