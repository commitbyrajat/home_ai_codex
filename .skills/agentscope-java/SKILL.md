---
name: agentscope-java
description: Create, extend, or debug AgentScope Java ReActAgent and HarnessAgent applications using the local OpenAI-compatible LiteLLM endpoint, engineering-auto model, and stack .env API key. Includes annotated tools, streaming, and session persistence; not for React UI development or unrelated Java agent frameworks.
---

# AgentScope Java

Deliver runnable Java code using the AgentScope version appropriate to the project. Preserve the build system, package names, and application structure. Always configure model access through the user's OpenAI-compatible LiteLLM stack as described below.

## Required LiteLLM Connectiont

All AgentScope implementations must use the existing LiteLLM proxy.

### Configuration Rules

- Use Spring Boot `application.yaml` or `application.properties` to load configuration.
- Use `API_BASE`, defaulting to `http://127.0.0.1:4000/v1`.
- Use `MODEL_NAME`, defaulting to `engineering-auto`.
- Load `API_KEY` securely from the environment; never hardcode or log credentials.
- Use `@ConfigurationProperties` for type-safe configuration binding.
- Always use `agentscope-extensions-model-openai` with an explicit `OpenAIChatModel`.
- Inject the configured model into `ReActAgent`, `HarnessAgent`, and other model-consuming components.
- Use the correct LiteLLM endpoint for the application's network environment.
- Fail startup if required authentication configuration is missing.

### application.yaml

```yaml
litellm:
  api-base: ${API_BASE:http://127.0.0.1:4000/v1}
  model-name: ${MODEL_NAME:engineering-auto}
  api-key: ${API_KEY}
```

### Alternative: application.properties

```properties
litellm.api-base=${API_BASE:http://127.0.0.1:4000/v1}
litellm.model-name=${MODEL_NAME:engineering-auto}
litellm.api-key=${API_KEY}
```

### Java Integration

- Bind the `litellm` properties using Spring Boot `@ConfigurationProperties`.
- Create a Spring-managed `OpenAIChatModel` bean using the configured base URL, model name, and API key.
- Inject the model bean into AgentScope agents.
- Follow the installed AgentScope version's supported builder API.

**Principle:** Use Spring Boot externalized configuration, dependency injection, and the existing LiteLLM proxy for all agent model connections.

## Inspect and select

Inspect repository instructions, existing agent code, Maven/Gradle dependencies, and Java version before editing. Check `java -version` and the build tool's Java runtime. AgentScope v2 requires Java 17+; the official quickstart recommends Maven 3.9+.

For an existing application, retain its AgentScope major version unless migration is requested or needed and explained. For a new application, verify the current stable release using [the source map](references/sources.md). The bundled starter targets **2.0.4**, checked on **2026-11-14**. Repository `main`, search snippets, hosted docs, GitHub releases, and Maven metadata can differ. A Maven `<release>` value can be a beta; inspect the version list and release status. Match APIs against the selected tag and confirm the artifacts resolve. Keep AgentScope modules at one version.

Choose the implementation from the request:

| Need | Implementation and dependencies |
| --- | --- |
| Explicit ReActAgent, a small tool loop, or app-managed infrastructure | `ReActAgent`: `agentscope-core` plus one model extension |
| Workspace persona, durable sessions, memory compaction, skills, or subagents | `HarnessAgent`: `agentscope-harness` plus one model extension; core is transitive |

For an unspecified small agent, start with ReActAgent. For a workspace-based or long-running agent, use HarnessAgent. Do not introduce a service deployment, Spring Boot, distributed storage, or multiple agents unless the task needs them.

Read [implementation patterns](references/implementation.md) for LiteLLM setup, a complete HarnessAgent example, streaming, and optional capabilities. Read [v2 compatibility and troubleshooting](references/v2-compatibility.md) when adapting old examples, upgrading, or debugging.

## Implement

1. Add the chosen framework artifact and `agentscope-extensions-model-openai`. `agentscope-core` alone does **not** contain the concrete provider. Put explicit AgentScope versions in a shared property, or use the project's verified dependency management. Preserve unrelated POM/Gradle settings.
2. Use `io.agentscope.core.ReActAgent` or `io.agentscope.harness.agent.HarnessAgent`. Set a useful system prompt, model, toolkit when needed, and a bounded `.maxIters(...)`.
3. Build `OpenAIChatModel` explicitly with the derived LiteLLM base URL, `.modelName("engineering-auto")`, and the key loaded from the stack `.env`; see `LiteLlmModel.java` in the starter. Pass `.model(model)` to the agent. A bare registry string does not establish the required endpoint and credential. Check signatures for the selected release rather than guessing timeout or option methods.
4. Register public Java tool methods using `@Tool`, explicit `@ToolParam(name = ..., description = ...)`, and `Toolkit.registerTool(instance)`. Use accurate descriptions and types. Set `readOnly` and `concurrencySafe` only when true. Validate business inputs inside the tool; optional primitive parameters otherwise receive default values.
5. Use `agent.call(List.of(new UserMessage(input)), context)` with a per-request `RuntimeContext` containing the intended `userId` and `sessionId`. In 2.0.4, `call(Msg, RuntimeContext)` exists on HarnessAgent but not ReActAgent; the list form works for both. In server code, derive user identity from authenticated application context. Reuse the same identifiers for follow-up turns; change them for independent conversations. The framework serializes a session within one agent instance; cross-process coordination requires a suitable store and deployment configuration.
6. For a ReAct agent that must remember turns, explicitly choose a state store: `InMemoryAgentStateStore` for process-local demos/tests or `JsonFileAgentStateStore` for local durability. HarnessAgent defaults to local JSON state outside its workspace; select distributed storage only when needed. Namespace stores/workspaces for independent agents as well as users/sessions.
7. `call(...)` returns `Mono<Msg>`; `streamEvents(...)` returns a `Flux` of typed events. Return/compose these publishers in reactive services. Use bounded `.block(Duration)` or `.blockLast(Duration)` only at a CLI/test or other blocking boundary. Do not block a WebFlux event-loop thread or create a second subscription that repeats the model call.
8. Close agent instances at CLI exit or application shutdown. Manage separately owned MCP clients and other resources according to their lifecycle contracts.

Keep the key in the source stack `.env` or its read-only runtime mount. Generated example env files may contain paths and variable names, never real keys. Document the LiteLLM address and fixed model alias. Do not silently switch providers when credentials are missing.

For tool execution that changes external state, implement the application's required permission/HITL path. A suspended call is not a completed operation. Preserve the default permission behavior; do not use global `BYPASS` to make a sample work. Register only the capabilities the use case needs.

## Starter assets

For a new standalone Maven ReAct project, adapt [assets/react-agent](assets/react-agent):

- `pom.xml`: Java 17 release target, AgentScope 2.0.4 core and OpenAI-compatible extension, JUnit, compiler/Surefire/exec plugins.
- `src/main/java/example/LiteLlmModel.java`: authenticated LiteLLM model, fixed `engineering-auto`, runtime key loading from the stack `.env`.
- `src/main/java/example/AgentApp.java`: CLI, per-call context, bounded execution, optional `--stream`.
- `src/main/java/example/CalculatorTools.java`: a read-only, thread-safe annotated tool.
- `src/test/java/example/AgentTest.java`: a scripted local model tests actual tool dispatch and conversation isolation without credentials.
- `src/test/java/example/LiteLlmModelTest.java`: local HTTP stub verifies the request path, model alias, and bearer authentication using a synthetic key.
- `.gitignore`: build output, local agent state/workspace, and secret env files.

Copy only into a new target or merge individual files after inspecting an existing project. Adapt artifact/package names and refresh the LiteLLM address from Compose; retain the required model and authentication. For a core-only app, do not add harness just to make a dependency available. The HarnessAgent variant is in the implementation reference.

From the generated project:

```bash
mvn verify
# Runtime reads LITELLM_MASTER_KEY from the stack .env; do not paste it into commands.
mvn exec:java -Dexec.mainClass=example.AgentApp
mvn exec:java -Dexec.mainClass=example.AgentApp -Dexec.args=--stream
```

The model is fixed to `engineering-auto`; there is no model-name override. `.env.example` documents optional `LITELLM_BASE_URL` and `LITELLM_ENV_FILE` settings for the same stack. The Java app reads process environment variables, so an application-local `.env` must be loaded by its launcher to set those optional values. Verify the router's tool-calling behavior before claiming live compatibility.

## Verify and hand off

Compile/package and run the project's relevant tests. Keep local agent tests deterministic using a scripted `Model`; check that the loop actually executes the tool and receives its result, rather than merely asserting a canned final answer. When the app supports multiple users, verify isolation with the same session id under distinct users. If persistence is required, verify recovery using a new instance and the intended persistent backend. These checks serve different claims: in-memory isolation does not demonstrate restart recovery.

Run a bounded live-model smoke test only when credentials are available and the task authorizes provider use. If unavailable, complete compilation and offline tests and clearly report the live call as not run. Do not hide missing keys, unresolved artifacts, zero discovered tests, or failed builds.

Provide the changed project path, agent/provider/version choice, env variable names, exact build/run commands, tests actually executed, and any unverified live or deployment behavior. For new applications, include concise run instructions in that application. Do not claim production durability from the default local store.
