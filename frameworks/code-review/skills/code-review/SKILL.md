---
name: code-review
description: Review code changes with six independent Luna reviewers for concurrency and state integrity, test quality, architecture and excess complexity, project conventions, critical OWASP vulnerabilities, and fidelity to the specification. Use for a requested code review; this does not replace specification review.
---

# Independent code review

Run all six roles, then synthesize evidence-backed findings. This is a portable native Codex workflow, with no external model runner or API key. A standalone invocation authorizes review, not implementation fixes or installation changes.

## Freeze the review scope

Identify the repository, requested change and comparison baseline. Record base/head commits and any staged, unstaged and untracked files in scope. For working-tree changes record content hashes or use an immutable temporary snapshot; a HEAD identifier alone does not identify uncommitted code. Include relevant tests and necessary dependency/configuration files. Do not reset, stash, or discard user work to prepare a review.

Keep the reviewed code fixed during each round. If it changes, discard affected conclusions and review the new recorded revision. Reviewers may inspect narrowly relevant surrounding code, callers and configuration to establish reachable behavior. Do not give them the entire repository or conversation as a context dump.

For the fidelity role, collect the actual specification plus relevant design/tasks, the original user prompt, later clarifications and explicitly approved decisions. Preserve wording and assign stable U-01, U-02, etc. references to user inputs. Separate proposals from approvals. Freeze specification inputs too. If a required baseline is missing, request it while running independent roles; mark fidelity incomplete, rather than reconstructing intent from the implementation or silently treating the prompt as an approved specification.

## Build separate role packets

Every packet contains only the role instructions, response language, repository root, exact revision/diff or snapshot paths, scoped file paths, necessary project constraints and known access limitations. Give reviewers access to reviewed code and relevant tests; these are essential evidence, not inherited task history. Applicable host instructions still apply.

Add only the role-specific inputs below. Never send the author's reasoning, suspected defects, preferred verdict, other reviewers' reports, or unrelated chat history. Do not send specifications and user prompts to roles that do not need them. If a role discovers that a particular requirement is essential to its check, it must request the exact missing fragment from the parent and explain why; the parent may supply that fragment without forwarding the whole conversation.

| Role / TOML file | Review scope | Additional inputs |
| --- | --- | --- |
| code-concurrency | Concurrent actions, retries and state integrity | Relevant transaction, state ownership, retry and idempotency contracts, where available |
| code-tests | Whether tests demonstrate behavior and fail for relevant regressions | Changed tests, tested production paths, test commands/configuration; a specific expected-behavior fragment only if essential |
| code-architecture | Fit with existing project boundaries and proportional complexity | Architecture guidance in AGENTS.md/README.md and targeted existing abstractions/callers |
| code-style | Consistency with documented project conventions | Applicable AGENTS.md and README.md paths/sections; no task prompt or specification |
| code-security | Only critical, exploitable OWASP vulnerabilities | Relevant trust boundaries, entry points and security configuration; no task prompt or specification by default |
| code-spec | Exactly the specified behavior: no omissions, deviations or extra scope | Frozen specification/design/tasks, original user prompt, clarifications and approved decisions with U-IDs |

## Dispatch independently

Read each of the six role definitions from `{{agents_path}}/<role>.toml`. Use each file's developer_instructions, model and model_reasoning_effort; defaults are gpt-6-luna and high, matching spec-review. Respect explicit installation overrides. Do not change the main model or global subagent defaults.

Use named roles if supported with fresh history. Otherwise read the TOML and pass its developer_instructions explicitly as the subagent task, with explicit model and reasoning effort. Merely naming a role does not load its definition. Every reviewer must be spawned with `fork_turns="none"` where available. Pass only its role-specific packet. If history-free spawning or a configured model is unavailable, disclose the affected incomplete checks; do not replace them with inherited-history agents, the main model, or the author's own review.

Launch as many roles concurrently as available slots allow; use waves when fewer than six slots are available. Never omit a role because of the concurrency limit. Keep first-round reviewers independent and do not forward their findings to one another. Reviewers do not edit reviewed files, fix code, delegate work, or execute commands that mutate the reviewed checkout. They may run safe targeted tests in an isolated scratch copy with required dependencies when permitted; otherwise state the execution limit. Distinguish executed results from static assessment.

### Missing code-style documentation

The style reviewer first checks applicable AGENTS.md and README.md, including scoped guidance relevant to changed files. It must not scan the whole project to derive its own code style. If necessary conventions are absent, it returns an incomplete style check and an explicit request to the parent to launch a separate documentation subagent.

The parent launches that separate subagent with fresh history, Luna/high (or the installed code-style configuration), repository paths and only the missing-conventions request. Its responsibility is to inspect a representative, targeted set of existing files and document supported conventions in the appropriate AGENTS.md. It is not a seventh reviewer and receives no prompt/specification or other findings. Tell it that it is not alone in the codebase, must preserve other edits and existing instructions, must not edit implementation files, and must distinguish observed conventions from new policy. Record examples/paths supporting the documented rules; do not canonize inconsistencies or infer rules from the proposed changes alone.

This workflow requests that documentation action; it does not grant additional filesystem permissions. If AGENTS.md cannot be written under existing permissions, report the limitation. Finish unaffected roles. When documentation is available, record the new guidance revision and rerun code-style with a fresh context against the same implementation revision. Treat material new guidance affecting another role as a changed input for that role. Do not claim the original incomplete style result passed.

## Synthesize

Wait for all six reports. Incomplete inputs, unavailable sources, errors and timeouts are not passes. A reasoned non-applicability result (for example no shared mutable state) may complete a role; a missing specification cannot establish fidelity.

Verify material evidence, merge duplicates retaining role attribution and reject unsupported preferences. Resolve conflicts using actual user requirements, the specification and verified project constraints. Keep questions separate from confirmed defects. Do not impose a findings quota. The security role reports critical vulnerabilities only; do not inflate lower-severity issues to fit that threshold or treat its clean report as a comprehensive security audit.

Return a concise report in the user's language containing the reviewed code/specification/guidance revisions, status and limits for each role, then actionable findings ordered by severity. Include file/line evidence, a concrete failure scenario, impact and minimal correction. State overall result: changes needed, no findings within the checked scope, or review incomplete. Never imply that passing this review proves all code correct or secure.

If the ongoing task authorizes fixes, the parent may apply justified changes and rerun affected roles with fresh packets on the new revision. Otherwise leave implementation files untouched. Limit to two review rounds per invocation unless the user requests more; the style documentation recovery counts as a rerun. Before declaring a final complete review, ensure all six results apply to the final inputs; carry forward a result only when its reviewed code and dependencies remain unchanged. Report remaining gaps rather than silently extending rounds.

Example: `$code-review Проверь изменения относительно main; исходный запрос и спека выше.`
