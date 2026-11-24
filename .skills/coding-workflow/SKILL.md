---
name: coding-workflow
description: Implement, fix, refactor, or test code using mandatory skill discovery, solution memory lookup, web research when memory lacks an applicable solution, and verified learning capture. Apply before every coding task, alongside relevant specialist skills.
---

# Coding Workflow

## Before coding: required gates

1. **Discover and read skills.** Call `skills-mcp.list_skills` before creating or modifying code, tests, build files, or runtime configuration. Read this skill and every relevant specialist skill using `get_skill` with the exact returned ids. Announce which skills you are applying. Discovery alone does not replace reading instructions. If MCP is unavailable, report it and inspect `~/.skills` directly; do not claim a successful MCP call.
2. **Analyze skills and publish a plan of action.** After reading the available applicable skills, analyze the task, current workspace evidence, and the requirements and constraints imposed by those skills. Before implementation, publish a concise, user-visible plan in the conversation covering the intended outcome, applicable skills, proposed approach, ordered steps (including memory lookup and any required web research), relevant assumptions or dependencies, and validation checks. Scale the detail to the task; even a small coding change requires a brief plan. An internal or unshared plan does not satisfy this requirement. Update the published plan if memory, research, or new evidence materially changes the approach. Publishing the plan does not itself require approval; proceed within the user-authorized scope unless a separate permission is required.
3. **Search for an existing solution in memory.** Call Graphiti `search_memory_facts` and/or `search_nodes` for the concrete problem, repository, framework/version, and exact error when relevant. Search group `main`: the current search schema uses `group_ids=["main"]`; writes use `group_id="main"`. Follow the exposed schema if it changes. Inspect linked episodes when needed to understand a candidate solution. Model recollection and conversation context do not substitute for this lookup.
4. **Assess applicability.** A memory hit counts as a solution only if it explains an actionable approach to the actual problem and fits the current code and runtime. Unrelated matches, preferences, stale versions, and incomplete facts do not satisfy the gate. Verify remembered assumptions against the workspace; never copy a remembered fix blindly.
5. **Search the web when memory has no applicable solution.** Invoke `gemini-search.web_search` before implementation. Search the specific problem, versions, and error; prefer official documentation or upstream sources. If memory covers only part of the task, research the unresolved part. Use returned source links; never invent citations. If no sources are returned, disclose that limitation. Current or changeable public facts still require verification even when memory contains a candidate solution. `ask` does not replace `web_search`.
6. **Handle unavailable services honestly.** If Graphiti fails, report that solution availability could not be determined and perform the web-search fallback. If the required web search also fails or is unavailable, report the blocker and continue only independent inspection or diagnostics; do not silently bypass the research gate or use another search service. Do not transmit secrets or private source code in search queries.

## Implement and validate

- Inspect repository instructions, existing code, dependencies, and working-tree changes before editing. Reuse established patterns and apply the relevant specialist skill's constraints.
- Make the smallest changes needed for the requested behavior. Preserve unrelated user changes, configuration, comments, and formatting. Modify only required sections of an existing `pom.xml`; never recreate or replace the entire POM.
- Verify the resulting behavior with appropriate tests, builds, or runtime checks. Fix failures and rerun affected checks. Distinguish passed checks from checks not run; do not label an unverified result successful.

## After successful work: required memory write

- After the task's relevant validation succeeds, call Graphiti `add_memory` with `group_id="main"` to save concise, reusable learnings. Do not stop at promising to save them.
- Record the problem and trigger, project/component and relevant versions, verified cause or approach, changed files/settings when useful, validation commands and outcomes, and applicability limits. Include useful research source URLs when available.
- Save the new solution, correction, decision, or preference rather than duplicating an existing episode without new information. If there is no new technical learning, record the successful application and validation of the existing solution concisely.
- Never store credentials, secrets, private data unnecessary for reuse, raw logs, or unverified explanations. Failed or incomplete work must not be saved as a successful solution.
- Check the write response. If ingestion is only queued, report it as queued; if saving fails, report that the learnings were not saved and include a short sanitized learning summary in the final response.
- Finish with the implemented behavior, validation evidence, and memory-write status.
