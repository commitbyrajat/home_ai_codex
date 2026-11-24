# Implementation patterns

Use the bundled ReAct starter for a minimal complete project. The following additions are conditional; do not add every integration to every app.

## Required authenticated LiteLLM model

Always add `io.agentscope:agentscope-extensions-model-openai`, aligned with core/harness, and import `io.agentscope.extensions.model.openai.OpenAIChatModel`. Use `LiteLlmModel.create()` from the starter to supply `.baseUrl(...)`, `.modelName("engineering-auto")`, and `.apiKey(...)` explicitly. Do not route around LiteLLM with another provider or change the alias to an upstream model.

The source stack is `/Users/rajatnigam/workspace/home_ai_stack/litellm-tev-stack`:

| Setting | Authoritative input | Checked value |
| --- | --- | --- |
| Host endpoint | `docker-compose.yml`, service `litellm`, published ports | `http://127.0.0.1:4000/v1` |
| Same Compose-network endpoint | `litellm` service DNS and internal port | `http://litellm:4000/v1` |
| Model | `config.yaml`, `model_list[].model_name` | `engineering-auto` |
| Key source | `config.yaml`, `general_settings.master_key` and stack `.env` | `LITELLM_MASTER_KEY` |

Re-read these files when generating an application. The alias routes to backends selected by LiteLLM's complexity router; agents must send the alias unchanged. The actual API-key value remains in the stack `.env`, which the starter reads at runtime. `LITELLM_ENV_FILE` selects a read-only mounted copy when deployed, and `LITELLM_BASE_URL` changes the network address of the same stack. No key is embedded in the skill or generated sources, and no OpenAI cloud key fallback is used.

The starter's key loader supports the current single-line literal dotenv assignment, optional `export`, single/double quotes, and trailing comments. It does not execute shell code or expand variable expressions. If the stack changes to more complex dotenv syntax, use a maintained dotenv parser rather than sourcing arbitrary content or silently passing an unresolved expression as the credential.

AgentScope 2.0.4's `OpenAIClient` normalizes a `/v1` base and its default `/v1/chat/completions` path. The final host request URL must be `http://127.0.0.1:4000/v1/chat/completions`, with `Authorization: Bearer <runtime key>` and JSON `model: engineering-auto`. Keep native structured output disabled until verified across the router's possible backends; the framework can use its tool-based fallback.

For Spring Boot, configure the existing model bean with the same explicit LiteLLM base URL, alias, and runtime credential. Do not add an unused model alongside the bean that agents actually inject. Keep HTTP authentication and business authorization in existing application layers. Return reactive publishers from WebFlux endpoints.

## HarnessAgent with restart persistence

Replace the starter's core dependency with `agentscope-harness`, retaining the OpenAI-compatible extension and `LiteLlmModel.java`. Add this class as `src/main/java/example/HarnessApp.java` when the request needs workspace and durable state:

```java
package example;

import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.message.Msg;
import io.agentscope.core.message.UserMessage;
import io.agentscope.harness.agent.HarnessAgent;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Objects;

public final class HarnessApp {
    public static void main(String[] args) {
        String prompt = args.length == 0 ? "Remember that my project is called Atlas." : args[0];
        RuntimeContext context = RuntimeContext.builder()
                .userId("local-user").sessionId("atlas-session").build();
        try (HarnessAgent agent = HarnessAgent.builder()
                .name("atlas-assistant")
                .agentId("atlas-assistant")
                .sysPrompt("Help the user with their project. Ask when information is missing.")
                .model(LiteLlmModel.create())
                .workspace(Path.of(".agentscope/workspace"))
                .maxIters(8)
                .build()) {
            Msg reply = Objects.requireNonNull(agent.call(List.of(new UserMessage(prompt)), context)
                    .block(Duration.ofMinutes(2)), "Agent returned no reply");
            System.out.println(reply.getTextContent());
        }
    }
}
```

Run once with the default prompt, then in a new process ask about the project:

```bash
mvn exec:java -Dexec.mainClass=example.HarnessApp
mvn exec:java -Dexec.mainClass=example.HarnessApp -Dexec.args='"What is my project called?"'
```

The workspace is `.agentscope/workspace`, and the default local state directory is `~/.agentscope/state/<agentId>/`. State is outside the workspace; deleting only the workspace does not reset conversation state. `-Dagentscope.state.home=/chosen/base` overrides the state base. Scope paths/ids deliberately; fixed demo identifiers are not a multi-user server identity policy.

Workspace `AGENTS.md` supplies agent instructions; memory/skills/subagents are harness features. These workspace files belong to the generated application and are distinct from this Codex skill. Configure compaction or custom tools only when required; check `CompactionConfig` and the selected tag's builder. Harness registers built-in capabilities: inspect the toolkit and permissions for deployment instead of treating a workspace as an execution sandbox.

## Streaming

The starter's `--stream` branch shows text deltas and tool-call starts. Use `TextBlockDeltaEvent.getDelta()` and `ToolCallStartEvent.getToolCallName()`. Do not append a complete final answer to text already assembled from deltas. Handle errors and suspension separately from successful completion. Permission events require an application interaction/resume path; a text-only CLI does not implement that path.

## Optional capabilities

- Structured output: use the selected version's `ReActAgent.call(..., OutputClass.class, context)` overload, then its structured result accessor. Verify provider support/fallback behavior and validate the domain object. Do not invent a `.structuredOutput(...)` builder API.
- MCP: register a supported client through the toolkit and include compatible MCP SDK dependencies from the tagged documentation example POM. Verify transport, authentication, tool exposure, and client cleanup.
- Tool groups and skills: consult the tool/skill guide for on-demand disclosure. A Codex skill and a skill loaded by a running AgentScope agent are separate artifacts.
- Multi-replica service: choose shared state/workspace and the documented coordination strategy. Per-instance session serialization does not serialize independent JVMs. Verify conflict/retry behavior and side effects for the backend.
- Background recovery: discover current session APIs in the official index. Ordinary `call` and `streamEvents` suffice for request-scoped replies; do not assume an HTTP stream survives a disconnected client.

See [sources](sources.md) for the official references.
