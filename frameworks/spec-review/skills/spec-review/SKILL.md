---
name: spec-review
description: Review an existing specification with five independent lightweight reviewers for request alignment, excess requirements, missing requirements, factual grounding, and Critical User Journeys (user actions and observable outcomes). Use for a requested specification review or a five-reviewer pass, including OpenSpec, plain Markdown, and specifications in chat.
---

# Independent specification review

Run five specialized subagents and synthesize their evidence-backed findings. This workflow is global and format independent; it does not require OpenSpec, project configuration changes, an external runner, or an API key.

## Prepare one review packet

Identify the requested specification and its related design/tasks if in scope. Use the original user request, later user clarifications, and explicitly approved decisions as the intent baseline. Preserve wording for behavior and scope; assign stable U-01, U-02, etc. references to these inputs without recasting agent proposals as user approval. Include the current request when it modifies scope.

If no original request is available, ask for it while continuing internal-consistency and grounding checks where possible; alignment, excess, and gaps cannot receive a complete verdict without an intent baseline. Do not reconstruct user intent from the specification alone.

Give all five reviewers the same packet:
- Original request/clarifications and their IDs; approved decisions separated from proposed ones.
- Specification content or exact file paths and revision, with relevant design/tasks.
- Source references, repository root, and applicable project constraints. Distinguish author-supplied evidence from facts independently verified during review.
- The scope of this review and any known unavailable sources.

Freeze the specification for the duration of a round. For committed files record the commit and whether the working tree differs; for uncommitted documents identify content hashes or a temporary immutable copy; for chat content pass the same full text under a named revision. Do not describe a commit as the reviewed revision if uncommitted edits were actually reviewed. Keep sources tied to the version checked.

Do not include the author's reasoning, preferred verdict, suspected defects, previous reviewer findings, or unrelated conversation history in the first-round packet. Include all actual user constraints even if they challenge the draft. Retrieve only relevant context, not a whole repository dump.

## Dispatch five roles with fresh contexts

Read the global role files under `{{agents_path}}`:

| Role | Definition | Scope |
| --- | --- | --- |
| spec-alignment | spec-alignment.toml | Fidelity to the request and internal contradictions |
| spec-excess | spec-excess.toml | Unnecessary obligations and scope expansion |
| spec-gaps | spec-gaps.toml | Missing requested or demonstrably necessary behavior |
| spec-grounding | spec-grounding.toml | Source support for existing-system and external factual claims |
| spec-cuj | spec-cuj.toml | Critical User Journeys: user goals, actions, visible responses, and completion |

CUJ is a required part of this review. For user-facing changes, the specification must describe its critical in-scope user goals as end-to-end journeys with an actor, goal, entry context, ordered user actions and observable responses, and a recognizable outcome. Read spec-cuj.toml for the detailed review criteria and sources. An equivalent clearly identified or linked scenario is sufficient; a literal heading alone is not. For internal-only changes, explain the relation to an existing journey or explicitly justify why CUJ is not applicable instead of inventing screens. The CUJ reviewer must still run and return that reasoned applicability result. Keep requirement coverage (spec-gaps) distinct from journey walkthrough completeness (spec-cuj).

Use the installed agents directory listed above, including when it is a custom corporate path. Each TOML's developer_instructions defines the review behavior; its model and model_reasoning_effort define the reviewer configuration. Do not change the main agent's model or general subagent defaults.

Explicitly use subagents for these five independent checks. They must start without inherited parent conversation history. When the spawn tool exposes fork_turns, set fork_turns="none". Pass only the role instructions and the common packet. Use named custom roles if the runtime supports selecting them while disabling history inheritance. If the tool has no named-role selector, read the role TOML and pass its developer_instructions as the task instructions, with its explicit model and reasoning effort; do not merely mention the role name and assume it was loaded.

System, applicable project instructions, permissions, and available tools can still be supplied by the host; fresh history does not mean a separate security boundary. If history-free spawning is unavailable, disclose the limitation and do not silently substitute inherited-context agents. If a configured model or role is unavailable, report the affected check and do not silently substitute the main model.

Run as many reviewers concurrently as the current session permits; with fewer slots, use waves until all five checks finish. A concurrency cap must not cause a role to be omitted. Do not share first-round reviewer outputs with other reviewers. Reviewers may inspect sources but must not modify reviewed files, implement code, or delegate more work. Wait for all five reports; an error, timeout, missing baseline, or inaccessible material is an incomplete check, not a pass.

## Synthesize and hand back

Read the five reports, verify material evidence, and merge duplicates while preserving which roles found them. Separate confirmed defects, questions needing a user decision, and optional suggestions. Do not automatically accept every finding or decide by vote. Resolve competing findings against the original request and verified constraints; explain unresolved conflicts.

Return a compact report in the user's language with:
- The reviewed revision and a status for each of the five roles, including coverage limitations.
- Actionable findings ordered by severity with specification locations, evidence, and minimal corrections.
- Overall readiness: ready within checked scope, changes needed, or review incomplete; state unresolved material decisions.

Standalone invocation reviews only: do not edit the specification or start implementation. If the ongoing user task already authorizes corrections, the parent may apply justified fixes and rerun affected roles on a new recorded revision. Limit to two review rounds per invocation unless the user requests more; surface remaining disagreements. A previous verdict becomes stale for any materially changed input; before declaring readiness ensure all five roles have applicable complete results for the final revision. Do not automatically add requirements, approve a proposal, or treat a review result as permission to implement.

Example invocation: `$spec-review Проверь эту спеку пятью ревьюерами; исходный запрос выше.`
