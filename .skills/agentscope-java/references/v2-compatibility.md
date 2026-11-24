# AgentScope v2 compatibility and troubleshooting

These notes describe the 2.0.4 baseline. Confirm against the selected release before changing an existing application.

## Avoid mixing v1 and v2 examples

| Legacy pattern | v2 approach |
| --- | --- |
| Provider implementations under `io.agentscope.core.model.*` | Add a provider extension; import `io.agentscope.extensions.model.<provider>.*` |
| Provider formatter under `io.agentscope.core.formatter.<provider>.*` | Use the extension's `.formatter.*` package |
| `.memory(Memory)` / `.statePersistence(...)` | `.stateStore(AgentStateStore)` and state scoped by runtime user/session |
| `SessionManager` | Automatic load/save through `AgentStateStore` |
| Hook-only streaming recipes | `streamEvents(...)` and typed events; use middleware for lifecycle interception |
| Old pipeline/MsgHub orchestration APIs | Check the v2 migration and subagent guides; do not invent old pipeline imports |

The implementation is `io.agentscope.core.ReActAgent`, not `io.agentscope.core.agent.ReActAgent`. The Java class spelling is `ReActAgent`.

**Verified 2.0.4 overload pitfall:** the HarnessAgent quickstart uses `agent.call(new UserMessage(text), context)`. HarnessAgent provides this convenience overload, but ReActAgent does not. When adapting that code to ReActAgent, use `agent.call(List.of(new UserMessage(text)), context)`, which works for both agent types. The `call(String, RuntimeContext)` overload also exists on both. ReActAgent's single-message `streamEvents(message, context)` overload is available; the two method families have different overload sets.

`UserMessage`, `SystemMessage`, and `AssistantMessage` provide role-specific constructors. User content cannot contain arbitrary tool result blocks; validation occurs during message construction. For HITL/tool-result resumption, use the documented message/event pattern with matching call ids.

When writing a scripted `Model` for tool-loop tests, include serialized argument JSON in `ToolUseBlock.content` as well as its structured `input` map. The streaming accumulator in 2.0.4 reconstructs arguments from raw content; an input-only fake can produce empty arguments and schema-validation failures. The bundled test demonstrates the working shape.

## Diagnose from the failing boundary

| Symptom | Check and correction |
| --- | --- |
| Provider class missing / model id unresolved | Verify extension artifact, imports, aligned versions, and runtime classpath. In a shaded JAR preserve ServiceLoader descriptors under `META-INF/services`. |
| Unsupported builder method | Compare the chosen release's source to the example; a `main` example can target an unreleased API. |
| Missing API key / authentication error | Verify the stack `.env` has a nonempty `LITELLM_MASTER_KEY`, the runtime can read it, and requests send bearer authentication. Never print the key or fall back to a cloud provider/dummy key. |
| Wrong destination / model not found | Re-read the stack Compose/config files. Set the explicit LiteLLM base URL and exact alias `engineering-auto`; check container networking and the final `/v1/chat/completions` path. Do not replace the alias with a backend name. |
| Tool absent from model request | Confirm public method/class, annotations, registration, exact tool name, active group, and tool-capable model. |
| Wrong/missing tool arguments | Use explicit `@ToolParam.name`, schema-friendly types, accurate `required` values, and validation; inspect schema and sanitized arguments. |
| Tool never executes / call suspended | Inspect termination reason and permission/HITL events. Resolve approval or external execution through the documented resume flow, retaining session and call ids. |
| Conversation forgets | Check state store configuration and identical user/session identifiers; a new in-memory store loses prior state. |
| Another user sees earlier conversation | Check authenticated identity, runtime ids, store/workspace namespaces, and custom tool fields. Avoid per-request mutable data on singleton tools. |
| Works on one node, fails after restart or elsewhere | Local JSON/in-memory stores are insufficient for cross-node recovery; check the production guide for state, workspace, locks, snapshots, and version conflicts. |
| WebFlux blocking error / stalls | Return or compose `Mono`/`Flux`; move unavoidable blocking business I/O to an appropriate bounded scheduler. CLI blocking examples are not controller templates. |
| Too many model calls | Inspect tool errors and max-iteration termination; bound iterations and time. Retrying a whole turn can repeat tool side effects. |

See the [migration guide](https://java.agentscope.io/v2/en/docs/change-log) and [release notes](https://java.agentscope.io/v2/en/docs/others/release-notes) for version-specific changes.
