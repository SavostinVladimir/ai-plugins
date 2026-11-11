---
name: code-review
description: Review code changes with seven independent Luna reviewers for concurrency and state integrity, test quality, architecture, overengineering and simplicity, established local project style, critical OWASP vulnerabilities, and fidelity to the specification. Use for a requested code review; this does not replace specification review.
---

# Independent code review

Run all seven roles, then synthesize evidence-backed findings. This is a portable native Codex workflow, with no external model runner or API key. A standalone invocation authorizes review, not implementation fixes or installation changes.

## When to run

During implementation, launch the full reviewer set once: after the main agent has written the first complete implementation and considers it ready for review. Do not launch reviewers while that implementation is still being written. A standalone explicit review request runs against the code the user names.

After this initial review, corrections requested by a human are a follow-up to the same change, not a trigger to launch all reviewers again. Make the authorized corrections and run appropriate targeted checks. Do not automatically restart the full set after each comment, fix, or review-driven edit. A fresh full review requires an explicit user request or a genuinely new implementation task reaching its first review-ready state; changed files alone do not make a new task. Keep this distinction across turns.

## Freeze the review scope

Identify the repository, requested change and comparison baseline. Record base/head commits and any staged, unstaged and untracked files in scope. For working-tree changes record content hashes or use an immutable temporary snapshot; a HEAD identifier alone does not identify uncommitted code. Include relevant tests and necessary dependency/configuration files. Do not reset, stash, or discard user work to prepare a review.

Keep the reviewed code fixed during each round. If it changes during a running review, invalidate affected conclusions and record the new revision. Any necessary targeted rerun uses that revision; this does not trigger another full run. Reviewers may inspect narrowly relevant surrounding code, callers and configuration to establish reachable behavior. Do not give them the entire repository or conversation as a context dump.

For the fidelity role, collect the actual specification plus relevant design/tasks, the original user prompt, later clarifications and explicitly approved decisions. Preserve wording and assign stable U-01, U-02, etc. references to user inputs. Separate proposals from approvals. Freeze specification inputs too. If a required baseline is missing, request it while running independent roles; mark fidelity incomplete, rather than reconstructing intent from the implementation or silently treating the prompt as an approved specification.

## Build separate role packets

Every packet contains only the role instructions, response language, repository root, exact revision/diff or snapshot paths, scoped file paths, necessary project constraints and known access limitations. Give reviewers access to reviewed code and relevant tests; these are essential evidence, not inherited task history. Applicable host instructions still apply.

Add only the role-specific inputs below. Never send the author's reasoning, suspected defects, preferred verdict, other reviewers' reports, or unrelated chat history. Do not send specifications and user prompts to roles that do not need them. If a role discovers that a particular requirement is essential to its check, it must request the exact missing fragment from the parent and explain why; the parent may supply that fragment without forwarding the whole conversation.

| Role / TOML file | Review scope | Additional inputs |
| --- | --- | --- |
| code-concurrency | Concurrent actions, retries and state integrity | Relevant transaction, state ownership, retry and idempotency contracts, where available |
| code-tests | Whether tests demonstrate behavior and fail for relevant regressions | Changed tests, tested production paths, test commands/configuration; exact user constraints on test level and placement; expected-behavior fragments only where needed |
| code-architecture | Fit with existing project boundaries and proportional complexity | Architecture guidance in AGENTS.md/README.md and targeted existing abstractions/callers |
| code-simplicity | Overengineering, unreachable defensive cases and the simplest readable solution | Targeted callers, types, boundary validation and existing helpers; exact user constraints on scope and unnecessary additions |
| code-style | Consistency with established local style and applicable conventions | Applicable AGENTS.md/README.md sections; nearest existing proto, implementation and test analogues; exact user clarifications on style, naming and test placement; no unrelated task history |
| code-security | Only critical, exploitable OWASP vulnerabilities | Relevant trust boundaries, entry points and security configuration; no task prompt or specification by default |
| code-spec | Exactly the specified behavior: no omissions, deviations or extra scope | Frozen specification/design/tasks, original user prompt, clarifications and approved decisions with U-IDs |

Label each supplied constraint by its source: user requirement (with exact wording/reference), project rule, or implementation decision. Do not present the author's implementation decisions as required behavior. Supply the role-relevant user constraints in the table proactively; preserving independence does not mean withholding them. Do not forward author justifications or expected findings.

For code-style, provide a focused handwritten diff including source proto and existing analogue paths outside the change. Keep generated artifacts available separately for targeted consistency checks. The reviewer must verify the examples and compare the prevailing local approach, not merely acknowledge the listed paths.

## Dispatch independently

Read each of the seven role definitions from `{{agents_path}}/<role>.toml`. Use each file's developer_instructions, model and model_reasoning_effort; defaults are gpt-6-luna and high, matching spec-review. Respect explicit installation overrides. Do not change the main model or global subagent defaults.

Use named roles if supported with fresh history. Otherwise read the TOML and pass its developer_instructions explicitly as the subagent task, with explicit model and reasoning effort. Merely naming a role does not load its definition. Every reviewer must be spawned with `fork_turns="none"` where available. Pass only its role-specific packet. If history-free spawning or a configured model is unavailable, disclose the affected incomplete checks; do not replace them with inherited-history agents, the main model, or the author's own review.

Launch as many roles concurrently as available slots allow; use waves when fewer than seven slots are available. Never omit a role because of the concurrency limit. Keep first-round reviewers independent and do not forward their findings to one another. Reviewers do not edit reviewed files, fix code, delegate work, or execute commands that mutate the reviewed checkout. They may run safe targeted tests in an isolated scratch copy with required dependencies when permitted; otherwise state the execution limit. Distinguish executed results from static assessment.

### Missing code-style documentation

The style reviewer checks applicable AGENTS.md/README.md and representative neighbouring examples for each applicable changed category. For style choices, preserve the prevailing local approach over a generic convention unless an explicit migration is required; surface conflicts with mandatory higher-priority instructions. Do not scan the whole project or infer a convention from one exception. Missing documentation alone does not make the check incomplete if local examples establish the convention. If mixed or insufficient examples and guidance leave the choice unresolved, mark that comparison incomplete and request a separate documentation subagent.

The parent launches that separate subagent with fresh history, Luna/high (or the installed code-style configuration), repository paths and only the missing-conventions request. Its responsibility is to inspect a representative, targeted set of existing files and document supported conventions in the appropriate AGENTS.md. It is not an eighth reviewer and receives no prompt/specification or other findings. Tell it that it is not alone in the codebase, must preserve other edits and existing instructions, must not edit implementation files, and must distinguish observed conventions from new policy. Record examples/paths supporting the documented rules; distinguish a prevailing local approach from isolated inconsistencies and never infer rules from the proposed changes alone.

This workflow requests that documentation action; it does not grant additional filesystem permissions. If AGENTS.md cannot be written under existing permissions, report the limitation. Finish unaffected roles. When documentation is available, record the new guidance revision and rerun code-style with a fresh context against the same implementation revision. Treat material new guidance affecting another role as a changed input for that role. Do not claim the original incomplete style result passed.

## Synthesize

Wait for all seven reports. Incomplete inputs, unavailable sources, errors and timeouts are not passes. A reasoned non-applicability result (for example no shared mutable state) may complete a role; a missing specification cannot establish fidelity.

Verify material evidence, merge duplicates retaining role attribution and reject unsupported preferences. Resolve conflicts using actual user requirements, the specification and verified project constraints. Keep questions separate from confirmed defects. Do not impose a findings quota. The security role reports critical vulnerabilities only; do not inflate lower-severity issues to fit that threshold or treat its clean report as a comprehensive security audit.

Before accepting complete code-style coverage, verify that it lists the inspected analogue paths and comparison results for every applicable changed category. A generic "AGENTS.md checked, no findings" is insufficient. Verify each reported mismatch against the frozen source; for style, a concrete mismatch supported by a rule, user constraint or prevailing local pattern is enough without a runtime failure scenario.

Return a concise report in the user's language containing the reviewed code/specification/guidance revisions, status and limits for each role, then actionable findings ordered by severity. Include file/line evidence, impact and minimal correction. Explain a concrete failure scenario, demonstrated unnecessary complexity, or, for style, the evidenced mismatch with the applicable convention or prevailing local approach. State overall result: changes needed, no findings within the checked scope, or review incomplete. Never imply that passing this review proves all code correct or secure.

If the ongoing task authorizes fixes, the parent may apply justified changes. Otherwise leave implementation files untouched. Recheck a specific affected role only when a material unresolved concern needs independent verification, with a fresh packet on the new revision; do not restart unaffected roles or the full set. Human follow-up corrections normally need only appropriate targeted checks. Limit to two review rounds per invocation unless the user requests more; the style documentation recovery counts as a rerun. Attribute reports to their reviewed revisions. Carry forward a result only when its reviewed code and dependencies remain unchanged; otherwise state that the changed part was not independently re-reviewed. Do not restart the full set just to claim all seven reports cover the final revision. Report remaining gaps rather than silently extending rounds.

Example: `$code-review Проверь изменения относительно main; исходный запрос и спека выше.`
