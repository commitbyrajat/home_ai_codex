# Codex Global Agent Instructions

## 1. Core Execution Policy

- Execute tasks using the smallest set of relevant tools, skills, and context.
- Prefer verified project context over assumptions.
- Avoid redundant tool calls, repeated discovery, and unnecessary explanations.
- Reuse results obtained earlier in the same task unless the underlying state changes.
- Never fabricate tool execution, retrieved information, validation results, or successful operations.
- Follow user instructions and applicable higher-priority policies over these defaults.
- Apply the Surgical File Editing Policy in Section 8 to all file modifications.

## 2. Automatic Skill Discovery — Skills MCP

**Server:** `skills-mcp`  
**Tools:** `list_skills`, `get_skill`  
**Source:** `~/.skills`

### Mandatory Rules

1. Before every coding task, call `list_skills` once to discover available skills.
2. Read `coding-workflow` using `get_skill` before modifying code, tests, dependencies, build files, or runtime configuration.
3. Automatically select and read additional skills whose descriptions match the task.
4. For non-coding tasks, discover skills when their use is relevant.
5. When the user explicitly names a skill, load it using the exact discovered skill ID.
6. Apply loaded skill instructions within the authorized task scope.

**Do not require explicit phrases such as "use available skills".**

### Optimization

- Discover skills once per task; reuse the catalog for subsequent steps.
- Read only relevant skills, not the entire catalog.
- Do not reload unchanged skills within the same task.
- Load updated skill content when explicitly requested or when changes are detected.
- If no specialist skill matches, proceed with `coding-workflow` for coding tasks.
- Briefly report selected skills; avoid verbose discovery logs.

### Fallback

If Skills MCP is unavailable, read applicable skills directly from `~/.skills`.

If neither source is accessible, report the limitation and proceed using available context, unless an explicitly required skill is essential.

## 3. Persistent Project Memory — Graphiti MCP

**Server:** `graphiti-memory`  
**Read tools:** `search_memory_facts`, `search_nodes`, `get_episodes`  
**Write tool:** `add_memory`  
**Group:** `main`

### Memory Retrieval

Search Graphiti before:

- Implementing or modifying an ongoing project.
- Making architectural or technical decisions.
- Troubleshooting recurring problems.
- Changing established project configuration.
- Performing work where previous solutions or preferences could materially affect the outcome.

Use `group_ids=["main"]` where supported by the exposed tool schema.

### Retrieval Strategy

1. Search using the actual problem, relevant technologies, and project identifiers.
2. Prefer `search_memory_facts` for known decisions and solutions.
3. Use `search_nodes` for related entities and broader context.
4. Use `get_episodes` only when additional historical detail is necessary.
5. Reuse relevant retrieved context without repeating searches unnecessarily.
6. Validate remembered solutions against the current workspace and runtime.

**Memory is contextual evidence, not authoritative proof of current behavior.**

### Memory Persistence

After a task produces a durable, verified result, record a concise episode using `add_memory` with `group_id="main"`.

Save only useful information:

- Problem and relevant context.
- Confirmed root cause, when established.
- Implemented solution or settled decision.
- Validation evidence.
- Important constraints and reuse limitations.

Do not save secrets, credentials, raw logs, speculative conclusions, or temporary troubleshooting steps.

Avoid duplicate memories. Update or supersede existing knowledge when supported by available tools; otherwise record only meaningful new information.

Verify and report the memory write status. Do not claim persistence without confirmation.

### Fallback

If Graphiti is unavailable:

- Use conversation and workspace context.
- Report the limitation briefly.
- Do not claim that memory was retrieved or saved.
- Follow the coding research fallback defined below.

## 4. Public Web Research — Gemini Search MCP

**Server:** `gemini-search`  
**Primary tool:** `web_search`  
**Supplementary tool:** `ask`

### Mandatory Search Policy

Use `gemini-search.web_search` whenever a task requires public internet research, including:

- Explicit web-search or online-verification requests.
- Current events, releases, prices, or changing information.
- Public URLs requiring retrieval or analysis.
- External documentation, APIs, GitHub repositories, and compatibility checks.
- Research, product comparisons, or troubleshooting requiring external evidence.
- Facts that cannot be reliably established from available local or conversation context.

**For public web research, `web_search` is mandatory even when the answer appears familiar.**

Use `ask` for supplementary reasoning or Google AI Mode exploration when useful. It does not replace mandatory `web_search`.

### Search Efficiency

1. Search using focused queries that target the unresolved question.
2. Prefer official documentation, primary sources, and maintained repositories.
3. Reuse relevant results from the current task.
4. Perform additional searches only to resolve missing information, contradictions, or important uncertainty.
5. Cite source links when available.
6. Clearly distinguish verified findings from inference.
7. Never invent search results, source contents, or citations.

Do not search merely to restate information already verified in the current task.

### Fallback

If Gemini Search MCP is unavailable:

- Report that required public web research could not be performed.
- Do not silently substitute another search provider or direct network access.
- Continue only with independent work that does not depend on unavailable research.
- Clearly identify any unresolved research dependency.

## 5. Mandatory Coding Workflow

Apply the following workflow to every coding task.

### Phase 1 — Discover

1. Call `skills-mcp.list_skills` once.
2. Load `coding-workflow` and relevant specialist skills.
3. Search Graphiti group `main` for prior solutions, decisions, and project constraints.
4. Inspect the relevant workspace, configuration, and existing implementation.
5. Identify the exact files and structural sections likely to require modification.
6. Inspect existing uncommitted changes before editing.

### Phase 2 — Research

Determine whether the retrieved memory contains a complete, applicable, verified solution.

- **Applicable solution exists:** Verify compatibility with the current workspace and proceed.
- **Partial or missing solution:** Call `gemini-search.web_search` for unresolved technical questions.
- **Graphiti unavailable:** Use workspace evidence and perform Gemini web research before implementation.
- **Gemini unavailable when required:** Report the blocker; perform only independent inspection or diagnostics.

Do not search the web redundantly when an existing solution is sufficient and no external verification is required.

### Phase 3 — Implement

1. Follow loaded skill instructions.
2. Prefer minimal, targeted changes consistent with existing architecture.
3. Identify the smallest relevant file section before making modifications.
4. Prefer contextual patches over complete file rewrites.
5. Preserve existing formatting, comments, ordering, and unrelated configuration.
6. Preserve established project conventions.
7. Avoid unnecessary refactoring or unrelated modifications.
8. Reuse existing dependencies and utilities when suitable.
9. Do not execute destructive or high-impact actions without appropriate authorization.
10. Follow all requirements in Section 8 — Surgical File Editing Policy.
11. Select installed structural inspection tools using Section 9 before applying localized edits.

### Phase 4 — Validate

1. Inspect the resulting diff and confirm that changes remain within the authorized scope.
2. Run `git diff --check` for tracked files when Git is available.
3. Verify that unrelated sections and pre-existing user changes remain unchanged.
4. Run relevant tests, checks, or builds when available.
5. Investigate failures using actual error output.
6. Verify that the implementation addresses the original problem.
7. Distinguish successful validation from untested assumptions.
8. Report any validation that could not be performed.

### Phase 5 — Persist

After successful implementation and validation:

1. Check whether the result provides reusable knowledge.
2. Save concise, verified learnings to Graphiti group `main`.
3. Avoid duplicate or low-value memories.
4. Confirm whether the write succeeded, was queued, or failed.

Do not record an unvalidated implementation as a confirmed solution.

## 6. Tool Invocation Priority

For coding tasks, follow this order:

**Skills discovery → Graphiti retrieval → Workspace inspection → Conditional Gemini research → Surgical implementation → Diff validation → Graphiti persistence**

This order defines the default workflow, not a requirement to call every tool when its conditions are not met.

### Efficiency Rules

- Skills: Discover once per task.
- Graphiti: Search once initially; search again only when a materially different problem emerges.
- Gemini: Search only unresolved external questions, except when the user explicitly requests web research.
- Workspace: Inspect only relevant files and dependencies.
- Editing: Apply the smallest contextual patch necessary; use Section 9 tools for structural targeting when beneficial.
- Validation: Verify the diff first, then run the smallest meaningful checks, expanding when necessary.
- Memory writes: Persist only durable, verified outcomes.

## 7. Response Policy

Keep responses concise and outcome-oriented.

For coding tasks, report:

- **Skills:** Relevant skills used.
- **Implementation:** Changes made, including affected files and sections.
- **Validation:** Tests, diff checks, or builds performed and their results.
- **Memory:** Saved, skipped, queued, or failed.
- **Limitations:** Only material blockers or unresolved issues.

Avoid repetitive status messages, unnecessary reasoning narration, and lengthy tool-execution summaries.

Do not claim success without evidence.

## 8. Surgical File Editing Policy

### 8.1 Mandatory Scope Identification

Before modifying any file:

1. Identify the exact target file or files.
2. Identify the smallest structural section, function, class, property, or configuration block requiring modification.
3. Inspect the surrounding context to understand dependencies and existing conventions.
4. Check for existing implementations, duplicate entries, and related configuration.
5. Inspect pre-existing changes to avoid overwriting user work.
6. Determine whether the requested change can be completed without modifying unrelated sections.

**Never modify an entire file when a localized change is sufficient.**

### 8.2 Minimal Patch Strategy

- Prefer `apply_patch` or equivalent contextual patch operations for localized changes.
- Use stable surrounding context to identify the intended modification location.
- Modify only the lines necessary to satisfy the requirement.
- Preserve existing indentation, whitespace, line endings, comments, ordering, and naming conventions.
- Avoid rewriting or regenerating complete files for small modifications.
- Do not run whole-file formatters when they would introduce unrelated changes.
- Avoid broad search-and-replace operations that may affect multiple unintended locations.
- Do not introduce unrelated refactoring, cleanup, dependency upgrades, or configuration changes.
- Use full-file generation only when creating a new file or when a complete rewrite is explicitly requested or technically necessary.
- When a broader modification is necessary, explain its scope and justification.

### 8.3 Structured File Editing

For XML, YAML, JSON, TOML, properties files, and other structured formats:

1. Identify the exact structural path before editing.
2. Distinguish identically named elements located in different scopes.
3. Preserve unrelated nodes, attributes, comments, and ordering.
4. Avoid serializers that unnecessarily rewrite or reorder the document.
5. Check whether the target entry already exists before adding another.
6. Preserve valid syntax and existing schema conventions.
7. Use structural parsers for inspection or validation when appropriate, while preferring minimal patches for localized edits.

Examples of structural targets:

- XML: `/project/dependencies`
- YAML: `spring.datasource.url`
- JSON: `compilerOptions.strict`
- TOML: `tool.ruff.lint`
- Java: a specific method, constructor, or class member
- Kubernetes: a specific resource and field path

### 8.4 Maven POM Editing Rules

When modifying `pom.xml`:

- Distinguish `/project/dependencies` from `/project/dependencyManagement/dependencies`.
- Distinguish `/project/build/plugins` from `/project/build/pluginManagement/plugins`.
- Identify whether dependencies or plugins are inherited from the parent POM.
- Respect dependency versions managed through BOMs and parent configuration.
- Do not add explicit versions when compatible versions are already managed.
- Check for existing dependencies before inserting new ones.
- Preserve existing dependency ordering and formatting conventions.
- Do not modify unrelated dependencies, plugins, properties, repositories, or Maven profiles.
- Do not modify parent versions, Java versions, or BOM versions unless required by the task.
- Prefer inserting, updating, or removing only the relevant dependency, plugin, or property block.

For Maven validation, use the smallest applicable check first, such as:

`mvn -q -f pom.xml validate`

Expand to compilation or tests when the change requires it.

### 8.5 Source Code Editing Rules

For Java, Python, JavaScript, TypeScript, Rust, and other source files:

- Identify the exact method, function, class, or statement requiring modification.
- Preserve public APIs and existing behavior unless changes are explicitly required.
- Avoid modifying unrelated methods or classes.
- Do not reorder imports unnecessarily.
- Do not rename unrelated symbols.
- Do not rewrite existing implementations when a small targeted change is sufficient.
- Preserve existing error-handling, logging, and testing conventions.
- Modify related tests only when necessary to validate the requested behavior.

### 8.6 Configuration and Infrastructure Editing

For Dockerfiles, Docker Compose, Kubernetes manifests, Helm charts, CI/CD pipelines, and application configuration:

- Identify the exact service, resource, stage, job, property, or configuration block.
- Preserve unrelated services, resources, environments, and deployment settings.
- Avoid changing security settings, network exposure, resource limits, or credentials unless required and authorized.
- Preserve existing environment-specific overrides.
- Do not regenerate complete manifests for localized configuration changes.
- Validate the modified configuration using appropriate tooling when available.

### 8.7 Diff-Based Verification

After every file modification:

1. Inspect the resulting diff.
2. Confirm that every changed line is necessary for the authorized task.
3. Check that unrelated sections remain unchanged.
4. Verify that pre-existing user modifications were preserved.
5. Run `git diff --check` when applicable.
6. Run syntax, configuration, compilation, or test validation as appropriate.
7. Correct unintended modifications introduced by the current task without discarding pre-existing user work.

Useful commands:

- `git status --short`
- `git diff --check`
- `git diff -- <file>`
- `git diff --cached -- <file>`

Remember that ordinary `git diff` does not show untracked files or all staged changes. Inspect those separately when relevant.

If the workspace is not managed by Git, compare the modified file against a preserved baseline or use an appropriate structural comparison.

### 8.8 Scope Violation Handling

If an implementation requires modifying files or sections outside the initially identified scope:

1. Determine whether the additional modification is genuinely necessary.
2. Prefer the smallest compatible extension of the scope.
3. Do not make unrelated changes merely because they appear beneficial.
4. Request clarification or authorization when the additional change materially expands the user's requested scope.
5. Report justified additional modifications in the final response.

Do not silently expand a localized task into a broad refactoring or configuration migration.

### 8.9 Completion Criteria

A file modification is complete only when:

1. The requested change has been implemented.
2. The correct file and structural section were modified.
3. The resulting file remains syntactically valid.
4. Unrelated sections remain unchanged unless justified.
5. Pre-existing user modifications are preserved.
6. The final diff contains only necessary changes.
7. Relevant validation has succeeded, or any limitations have been explicitly reported.

**Core principle: Identify the smallest target section, apply the smallest possible patch, preserve everything unrelated, and validate the final diff before reporting completion.**


## 9. Local macOS Surgical Editing Toolkit

The following Homebrew tools are already installed: `ast-grep`, `xmlstarlet`, `yq`, and `comby`. **Do not reinstall or upgrade them** unless explicitly authorized. These tools support, but do not replace, the surgical editing requirements in Section 8.

### 9.1 Tool Selection

| Target | Structural inspection | Preferred modification |
|---|---|---|
| Java, Python, JavaScript, TypeScript, Rust (supported syntax) | `ast-grep` | Small contextual `apply_patch` |
| Maven `pom.xml` and XML | `xmlstarlet` with XPath | Small contextual `apply_patch` |
| YAML, JSON, Kubernetes manifests, Helm values | Mike Farah `yq` | `apply_patch`; `yq -i` only if diff stays minimal |
| Cross-language template matching | `comby` | Reviewed contextual replacement or `apply_patch` |
| Dockerfiles, properties, other plain text | Targeted context inspection | `apply_patch` |

Choose one appropriate discovery tool; do not run every tool for every task. Before editing, verify the intended target exists and that the match count is as expected. For multiple matches, scope by file, class, namespace, resource name, or structural path. Prefer structural tools for **locating and validating** a target; a parser's in-place rewrite can reformat unrelated content.

### 9.2 Installed Version and Local Help

```bash
command -v ast-grep xmlstarlet yq comby
ast-grep --version && ast-grep run --help
xmlstarlet --version && xmlstarlet sel --help && xmlstarlet ed --help
yq --version && yq --help
comby -help
```

Check the installed CLI's help before using unfamiliar flags. If a command fails, inspect the error and installed-version help rather than guessing syntax. `yq` examples below require Mike Farah's implementation; verify with `yq --version`.

### 9.3 ast-grep — Source Code

Locate Java invocations (read-only):

```bash
ast-grep run --lang java --pattern 'calculateInterest($$$ARGS)' src/main/java
```

Preview a structural rewrite; do not apply it blindly:

```bash
ast-grep run --lang java \
  --pattern 'oldMethod($$$ARGS)' \
  --rewrite 'newMethod($$$ARGS)' src/main/java
```

Use the returned matches to locate the containing method/class, then prefer a minimal patch. Review the CLI help for interactive or bulk rewrite options before using them.

Official docs: https://ast-grep.github.io/

### 9.4 XMLStarlet — Maven POM / XML

Maven POM elements normally use a default XML namespace; bind a prefix for XPath queries. Inspect Java version:

```bash
xmlstarlet sel -N m='http://maven.apache.org/POM/4.0.0' \
  -t -v '/m:project/m:properties/m:java.version' pom.xml
```

Locate direct project dependencies (not dependency management or profiles):

```bash
xmlstarlet sel -N m='http://maven.apache.org/POM/4.0.0' \
  -t -m '/m:project/m:dependencies/m:dependency' \
  -v 'concat(m:groupId, ":", m:artifactId)' -n pom.xml
```

Preview a property edit **without** modifying the file:

```bash
xmlstarlet ed -P -N m='http://maven.apache.org/POM/4.0.0' \
  -u '/m:project/m:properties/m:java.version' -v '21' pom.xml
```

If XPath selects no element, the edit may silently have no effect; verify the selected node first. Avoid `-L` for localized changes unless XML serialization produces an acceptable diff. Validate with `xmlstarlet val -w pom.xml` and, when appropriate, `mvn -q -f pom.xml validate`.

Official docs: https://xmlstar.sourceforge.net/docs.php

### 9.5 yq — YAML and JSON

Read Spring Boot configuration:

```bash
yq '.spring.datasource.url' application.yaml
```

Inspect a specific Kubernetes Deployment in a possibly multi-document YAML file:

```bash
yq 'select(.kind == "Deployment" and .metadata.name == "smartwealth-api") | .spec.replicas' deployment.yaml
```

Preview a scoped update without writing:

```bash
yq '(select(.kind == "Deployment" and .metadata.name == "smartwealth-api") | .spec.replicas) = 3' deployment.yaml
```

Only after confirming the correct resource and reviewing the preview, optionally edit in place:

```bash
yq -i '(select(.kind == "Deployment" and .metadata.name == "smartwealth-api") | .spec.replicas) = 3' deployment.yaml
```

Immediately inspect the diff; if serialization changes unrelated content, restore **only the tool's unintended changes** without discarding user edits, and use `apply_patch` instead. Syntax checks: `yq '.' deployment.yaml` and `yq -p=json '.' config.json`. These parse checks do not guarantee schema correctness.

Official docs: https://mikefarah.gitbook.io/yq/

### 9.6 comby — Structural Template Matching

Inspect CLI help:

```bash
comby -help
```

Find matching invocations without editing:

```bash
comby 'oldMethod(:[args])' '' -match-only Example.java
```

Preview a proposed replacement (without `-in-place`):

```bash
comby 'oldMethod(:[args])' 'newMethod(:[args])' Example.java
```

Review every match before applying replacements, particularly across files. For a single change, prefer a contextual patch. `comby` is optional if another tool already identifies the target precisely.

Official docs: https://comby.dev/docs/overview

### 9.7 Documentation Lookup Policy

1. Use local `--help`, subcommand help, and installed version output first.
2. Consult the official documentation linked above for unclear behavior or advanced syntax.
3. When public documentation retrieval or version verification is required, follow Section 4 and use `gemini-search.web_search`; `ask` is supplementary only.
4. Do not invent flags, assume an example applies to a different version, or claim documentation was consulted when it was not.
5. Reuse verified documentation already retrieved in the same task.
6. Do not send secrets, proprietary code, or confidential configuration in external search queries.

### 9.8 Mandatory Edit Verification

For each modified file: **Locate → Inspect → Patch → Diff → Validate**.

```bash
git status --short
git diff --check
git diff -- path/to/file
git diff --cached -- path/to/file
```

Record pre-existing staged/unstaged changes before editing; normal `git diff` excludes staged and untracked files. For untracked files or non-Git workspaces, use a safe baseline comparison. Check that the change is present and that unrelated lines are untouched. Run format-specific parsing and the smallest meaningful tests/build checks. A successful parse alone does not prove behavioral correctness.

**Non-negotiable:** Structural targeting does not authorize a full-file rewrite. Use the smallest possible patch, preserve user changes, and report validation accurately.
