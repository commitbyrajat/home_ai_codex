# Official source map and research baseline

Checked **2026-11-14**. Recheck changing versions and provider settings when creating an application. These links are discovery aids; read the page or source relevant to the feature being implemented.

## Requested starting points

- [AgentScope Java repository](https://github.com/agentscope-ai/agentscope-java): framework modules, tagged source, examples, and release history.
- [Java v2 quickstart](https://java.agentscope.io/v2/en/docs/quickstart): Java/tooling requirements, HarnessAgent setup, provider module, runtime context, and streaming.
- [Documentation index](https://java.agentscope.io/llms.txt): discover current official pages. Hosted documentation also exposes `.md` versions.

## Version evidence

- [GitHub latest release API](https://api.github.com/repos/agentscope-ai/agentscope-java/releases/latest) returned `v2.0.4`, `prerelease: false`, published `2026-10-08T03:40:20Z`.
- [Release v2.0.4](https://github.com/agentscope-ai/agentscope-java/releases/tag/v2.0.4) is the baseline for bundled examples.
- [Maven Central core metadata](https://repo.maven.apache.org/maven2/io/agentscope/agentscope-core/maven-metadata.xml) lists `2.0.4` and `2.1.0-BETA1`. Both `latest` and `release` pointed to the beta during research. Do not equate those fields with latest stable.
- [Tagged root POM](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/pom.xml) sets Java 17 and revision 2.0.4. The starter uses that release target while allowing a newer installed JDK.
- The repository README displayed 2.0.3 dependencies while the hosted quickstart selected 2.0.4. Search results also exposed a draft release note. Prefer released artifacts plus tagged source when reconciling examples.

## Feature references

| Topic | Official documentation | Tagged source to check for exact signatures |
| --- | --- | --- |
| Agent builder, call, observe, structured output, HITL | [Agent](https://java.agentscope.io/v2/en/docs/building-blocks/agent) | [ReActAgent.java](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/agentscope-core/src/main/java/io/agentscope/core/ReActAgent.java) |
| Tool annotations, groups, MCP and skills | [Tool](https://java.agentscope.io/v2/en/docs/building-blocks/tool) | [ToolParam.java](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/agentscope-core/src/main/java/io/agentscope/core/tool/ToolParam.java), [Toolkit.java](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/agentscope-core/src/main/java/io/agentscope/core/tool/Toolkit.java) |
| Provider artifacts, model registry and builders | [Model](https://java.agentscope.io/v2/en/docs/building-blocks/model) | [Model extensions](https://github.com/agentscope-ai/agentscope-java/tree/v2.0.4/agentscope-extensions/agentscope-extensions-model) |
| Messages, content validation and typed events | [Message & Event](https://java.agentscope.io/v2/en/docs/building-blocks/message-and-event) | [Message package](https://github.com/agentscope-ai/agentscope-java/tree/v2.0.4/agentscope-core/src/main/java/io/agentscope/core/message) |
| Session context and state stores | [Context & AgentState](https://java.agentscope.io/v2/en/docs/building-blocks/context) | [State package](https://github.com/agentscope-ai/agentscope-java/tree/v2.0.4/agentscope-core/src/main/java/io/agentscope/core/state) |
| Harness capabilities | [Harness architecture](https://java.agentscope.io/v2/en/docs/harness/architecture) | [HarnessAgent.java](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/agentscope-harness/src/main/java/io/agentscope/harness/agent/HarnessAgent.java) |
| Permission requests and resuming | [Permissions](https://java.agentscope.io/v2/en/docs/building-blocks/permission-system) | [Permission package](https://github.com/agentscope-ai/agentscope-java/tree/v2.0.4/agentscope-core/src/main/java/io/agentscope/core/permission) |
| Migrating legacy examples | [V1 migration](https://java.agentscope.io/v2/en/docs/change-log) | [Tagged migration guide](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/docs/v2/en/docs/change-log.md) |
| Multiple replicas, durable storage, sandbox recovery | [Going to production](https://java.agentscope.io/v2/en/docs/others/going-to-production) | [Documentation examples](https://github.com/agentscope-ai/agentscope-java/tree/v2.0.4/agentscope-examples/documentation/src/main/java/io/agentscope/examples/documentation2) |

For advanced capabilities, discover workspace, compaction, middleware, subagent, and sandbox pages through the index. Those are optional application features, not prerequisites for a minimal ReActAgent.

## User-required LiteLLM stack

Checked the local `docker-compose.yml`, `config.yaml`, and presence/format of `LITELLM_MASTER_KEY` in `.env` at `/Users/rajatnigam/workspace/home_ai_stack/litellm-tev-stack`. The host binding is `127.0.0.1:4000:4000`, the required public model alias is `engineering-auto`, and `general_settings.master_key` references `os.environ/LITELLM_MASTER_KEY`. No secret value is recorded here. These local files govern connection settings instead of the upstream quickstart's provider examples.

- [Tagged OpenAIChatModel builder](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/agentscope-extensions/agentscope-extensions-model/agentscope-extensions-model-openai/src/main/java/io/agentscope/extensions/model/openai/OpenAIChatModel.java): explicit base URL, API key, model name, and streaming configuration.
- [Tagged OpenAIClient](https://github.com/agentscope-ai/agentscope-java/blob/v2.0.4/agentscope-extensions/agentscope-extensions-model/agentscope-extensions-model-openai/src/main/java/io/agentscope/extensions/model/openai/OpenAIClient.java): URL normalization and bearer-authenticated Chat Completions requests.
- [LiteLLM framework client examples](https://docs.litellm.ai/docs/proxy/lens/framework-examples): OpenAI-compatible base URL and gateway API-key setup.
