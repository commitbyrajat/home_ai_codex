# Setup Guide: Codex CLI + LiteLLM + Ollama + Gemini Search

This guide covers setting up **Codex CLI** with local LLM routing (LiteLLM → Ollama), and the **Gemini Search MCP** for web-enabled AI capabilities.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Ollama Models & macOS Configuration](#ollama-models--macos-configuration)
3. [Gemini Search MCP Setup](#gemini-search-mcp-setup)
4. [LiteLLM Gateway Setup (Project-Based)](#litellm-gateway-setup-project-based)
5. [Codex Configuration](#codex-configuration)
6. [Testing & Validation](#testing--validation)
7. [Troubleshooting](#troubleshooting)
8. [Quick Reference](#quick-reference)

---

## Prerequisites

### Required Software

| Component | Version/Observation | Notes |
|-----------|---------------------|-------|
| **OS** | macOS on Apple Silicon | Tested on M4 Pro |
| **Codex CLI** | 0.163.0 | `codex --version` |
| **Ollama** | 0.40.0 | Desktop app + CLI |
| **Docker Desktop** | Latest stable | Required for Docker Compose |
| **Docker Compose** | Included with Docker Desktop | `docker compose version` |
| **jq** | Any recent version | `jq --version` (for JSON logs) |

### Optional Dependencies

- `zsh` (default shell on modern macOS)
- Git repository access for Codex and Gemini Search images

---

## Ollama Models & macOS Configuration

### 1. Pull Required Models

```bash
ollama pull Qwen3.5:latest
ollama pull deepseek-r1:8b
ollama pull tev1:0.8b
ollama list
```

**Important:** Model names are case-sensitive where applicable; match `ollama list` and the LiteLLM configuration exactly.

### 2. Configure Context Window

Set a default context of **8192** for native macOS Ollama:

```bash
launchctl setenv OLLAMA_CONTEXT_LENGTH 8192
launchctl getenv OLLAMA_CONTEXT_LENGTH
```

**Crucial:** Fully quit and reopen the Ollama desktop application after changing this variable. A running `ollama serve` process will not inherit new environment values.

```bash
# Quit Ollama.app
osascript -e 'quit app "Ollama"'

# Verify server is stopped
pgrep -fl 'ollama serve'

# If processes remain, terminate gracefully
kill -TERM <PID>

# Restart Ollama desktop app
open -a Ollama

# Verify context window applied
ollama run Qwen3.5:latest 'Reply with OK.'
ollama ps
```

**Expected output:**
```text
NAME              SIZE     PROCESSOR   CONTEXT   RUNNER
Qwen3.5:latest    7.7 GB   100% GPU    8192      mlx
```

> **Note:** The model's advertised maximum context (262,144 for Qwen3.5) is not the same as its actively allocated context. `ollama ps` shows the actual runtime allocation. Larger context values increase memory usage.

### 3. Memory Usage Notes

After running Codex, typical allocations:
- Qwen3.5: ~10 GB (runtime fluctuates, may be higher than 7.7 GB download size)
- TEV (tev1:0.8b): ~1.9 GB

TEV may load with a different context (e.g., 2048) based on request-level configuration.

---

## Gemini Search MCP Setup

The `gemini-search` Compose service builds a local image and serves the MCP Streamable HTTP transport at `http://127.0.0.1:3000/mcp`. It uses 2 GB of shared memory for Chromium browser automation.

### Build the Image

```bash
cd gemini-search
docker compose build gemini-search
```

**Technical notes:**
- The local Dockerfile fetches repository source at a pinned commit
- Installs Playwright explicitly (the base repository Dockerfile invokes `npx playwright` without installing it)
- Caps MCP SDK below version 2 (uses v1 `FastMCP` API from upstream)
- Built and tagged as `gemini-search-mcp:codex`
- Targets `linux/amd64` architecture

> **Apple Silicon Note:** On M-series Macs, amd64 runs under Docker Desktop emulation. Browser automation will be slower than a native arm64 build. The current ARM64 cryptography wheel crashes with an illegal instruction during MCP startup on Apple Silicon.

### Start the Service

```bash
cd gemini-search
docker compose up -d --build gemini-search
docker compose ps gemini-search
```

### Verify Registration

The MCP server is registered only in `~/.codex/local.config.toml`, so start Codex with the local profile:

```bash
codex --profile local
```

This profile also selects LiteLLM. The default Codex profile remains on the OpenAI provider and does not register Gemini Search.

### Access noVNC Interface (Optional)

The Gemini Search container keeps a persistent Chromium profile and exposes a local-only noVNC view:

```
http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale
```

If Google presents a CAPTCHA, open this page in a browser and complete the challenge manually. The profile is saved in the `gemini-browser-profile` Compose volume and reused by later searches.

**Important:** The noVNC port is bound to host loopback (127.0.0.1) only—not accessible from external network interfaces.

### Technical Architecture

- Container port 3000 → Host loopback (MCP Streamable HTTP transport)
- The upstream repository's port 8080 is an OpenAI-compatible API, **not** the MCP transport
- This image starts the FastMCP server using Streamable HTTP
- Search availability depends on Google AI Mode and browser automation
- **No Gemini API key required** for this setup

---

## LiteLLM Gateway Setup (Project-Based)

This section covers setting up a persistent LiteLLM gateway in a dedicated project directory. This is recommended for production use rather than the Codex-profile approach below.

### 1. Create Project Directory

```bash
mkdir -p ~/workspace/home_ai_stack/litellm-tev-stack
cd ~/workspace/home_ai_stack/litellm-tev-stack
```

### 2. Environment Variables (.env)

Create `.env` (do NOT commit to source control):

```dotenv
LITELLM_MASTER_KEY=sk-local-change-me
```

### 3. LiteLLM Configuration

#### config.yaml

```yaml
model_list:
  - model_name: qwen-coder
    litellm_params:
      model: ollama_chat/Qwen3.5:latest
      api_base: http://host.docker.internal:11434
      api_key: ollama
    model_info:
      max_input_tokens: 262144

  - model_name: deepseek-reasoner
    litellm_params:
      model: ollama_chat/deepseek-r1:8b
      api_base: http://host.docker.internal:11434
      api_key: ollama
    model_info:
      max_input_tokens: 131072

  - model_name: engineering-auto
    litellm_params:
      model: auto_router/complexity_router
      complexity_router_config:
        context_compaction: false
        tiers:
          SIMPLE: qwen-coder
          MEDIUM: qwen-coder
          COMPLEX: qwen-coder
          REASONING: deepseek-reasoner
        classifier_type: jev
        jev_classifier_config:
          model: tev1:0.8b
          api_base: http://host.docker.internal:11434
          api_key: ollama
          timeout_ms: 15000
          circuit_breaker_enabled: true
          circuit_breaker_cooldown_seconds: 30
        classifier_fallback: heuristic
        classifier_context_window_size: 1
        classifier_context_budget_chars: 1000
        classification_mode: user_turn
        session_affinity: true
        session_affinity_ttl_seconds: 3600
        custom_technical_keywords:
          - spring
          - maven
          - java
          - react
          - kafka
          - postgres
          - concurrency
          - deadlock
      complexity_router_default_model: qwen-coder

litellm_settings:
  num_retries: 1
  request_timeout: 240
  drop_params: true

router_settings:
  set_verbose: true

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

#### compose.yaml

```yaml
services:
  litellm:
    image: docker.litellm.ai/berriai/litellm:main-stable
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### 4. Start LiteLLM Gateway

```bash
docker compose up -d
# or just start the gateway service
docker compose up -d litellm
```

### 5. Verify Gateway Health

```bash
# Check liveliness
curl -fsS http://localhost:4000/health/liveliness

# List available model aliases
curl -fsS http://localhost:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" | jq .

# Test the Responses API (critical for Codex compatibility)
curl -sS -i http://localhost:4000/v1/responses \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"engineering-auto","input":"Reply with OK"}'
```

> **Important:** Before relying on `engineering-auto`, confirm that your LiteLLM version supports `/v1/responses` including streaming and tool calls. Chat Completions support alone is **not** sufficient for Codex CLI compatibility.

---

## Codex Configuration

Two approaches are available:

### Approach A: Persistent Profile (~/.codex/config.toml)

Edit `~/.codex/config.toml` and **append or merge** the following TOML:

```toml
[model_providers.litellm]
name = "Local LiteLLM"
base_url = "http://localhost:4000/v1"
env_key = "LITELLM_API_KEY"
wire_api = "responses"
requires_openai_auth = false
request_max_retries = 2
stream_max_retries = 2
stream_idle_timeout_ms = 600000

[features]
multi_agent = true
shell_snapshot = true

[profiles.local]
model_provider = "litellm"
model = "engineering-auto"
```

**Critical:** Do not add duplicate `[model_providers.litellm]` or `[profiles.local]` tables; merge existing entries if necessary. The default Codex profile remains unchanged on OpenAI.

### Approach B: Session-Based Environment Variable

Append this function to `~/.zshrc`:

```bash
codex() {
  if [[ "${CODEX_BACKEND:-openai}" == "local" ]]; then
    command codex --profile local "$@"
  else
    command codex "$@"
  fi
}
```

Reload your shell:
```bash
source ~/.zshrc
```

**Usage:**
```bash
codex                                    # Original/default OpenAI backend
CODEX_BACKEND=local codex                # Local LiteLLM for one invocation
export CODEX_BACKEND=local               # Make local the default in this shell
codex                                    # Uses LiteLLM
unset CODEX_BACKEND                      # Restore original/default backend
codex                                    # Uses OpenAI again
```

Noninteractive example:
```bash
CODEX_BACKEND=local codex exec 'Explain this Spring Boot repository'
```

Explicit profile selection (bypasses wrapper):
```bash
command codex --profile local
```

> Note: `CODEX_BACKEND` is a shell-function implementation, not a native Codex configuration setting. New terminals will default to OpenAI unless you export it explicitly.

---

## Testing & Validation

### 1. Check LiteLLM Connectivity

```bash
curl -fsS http://localhost:4000/health/liveliness
```

### 2. Verify Model Aliases

```bash
curl -fsS http://localhost:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_API_KEY" | jq .
```

### 3. Test Responses API

```bash
curl -sS -i http://localhost:4000/v1/responses \
  -H "Authorization: Bearer $LITELLM_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"engineering-auto","input":"Reply with OK"}'
```

### 4. Smoke-Test Codex

```bash
CODEX_BACKEND=local codex exec 'Explain what dependency injection is in one sentence'
```

Check LiteLLM logs for which underlying model was selected:
```bash
docker compose logs --tail=150 litellm
```

> Run tests involving harmless tool calls or read-only repository inspection before permitting autonomous edits.

### 5. Advanced: Benchmark & Isolation Tests

#### Router test (with TEV):
```bash
codex exec \
  --skip-git-repo-check \
  --disable multi_agent \
  -c 'model_provider="litellm"' \
  -m engineering-auto \
  --sandbox read-only \
  --json \
  'Run pwd using the terminal tool and return only the directory path.' \
  > codex-router-test.jsonl

jq -c 'select(.type == "turn.completed" or .type == "turn.failed")' codex-router-test.jsonl
```

#### Direct Qwen test (bypassing TEV):
```bash
/usr/bin/time -p codex exec \
  --skip-git-repo-check \
  --disable multi_agent \
  -c 'model_provider="litellm"' \
  -m qwen-coder \
  --sandbox read-only \
  --json \
  'Run pwd using the terminal tool and return only the directory path.' \
  > codex-direct-qwen.jsonl

jq -c 'select(.type == "turn.completed" or .type == "turn.failed")' codex-direct-qwen.jsonl
```

#### Direct Ollama inference test:
```bash
curl -sS http://localhost:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen3.5:latest",
    "messages": [{"role": "user", "content": "Reply with exactly OK."}],
    "think": false,
    "stream": false
  }' | jq '{
    response: .message.content,
    total_seconds: (.total_duration / 1e9),
    load_seconds: (.load_duration / 1e9),
    prompt_eval_count,
    prompt_eval_seconds: (.prompt_eval_duration / 1e9),
    eval_count,
    eval_seconds: (.eval_duration / 1e9)
  }'
```

### 6. Inspect Runtime Metrics

```bash
ollama ps
```

**Sample output:**
```text
NAME              SIZE     PROCESSOR   CONTEXT   RUNNER
Qwen3.5:latest    7.7 GB   100% GPU    8192      mlx
tev1:0.8b         1.9 GB   25% CPU     2048      mlx
```

> Note: Runtime memory usage fluctuates between runs and may differ from download sizes.

### 7. Analyze JSONL Logs

```bash
# Filter completed/failed turns
jq -c 'select(.type == "turn.completed" or .type == "turn.failed")' codex-router-test.jsonl

# Extract errors
jq -c 'select(.item.type == "error")' codex-router-test.jsonl

# Detailed breakdown
jq -r '[.type, (.item.type // ""), (.message // "")] | @tsv' codex-router-test.jsonl
```

---

## Troubleshooting

| Symptom | Check/Resolution |
|---------|------------------|
| `401 Unauthorized` | Verify `LITELLM_API_KEY` matches the running gateway's master key. Export it in your session: `export LITELLM_API_KEY=your_key` |
| `404` on `/v1/responses` | LiteLLM version/router may not support Responses API for `engineering-auto`. Confirm `/v1/responses` endpoint before testing Codex. |
| Model not found | Confirm the alias appears in `/v1/models` and matches `engineering-auto`, `qwen-coder`, or `deepseek-reasoner`. Verify models are pulled: `ollama list` |
| CLI unexpectedly uses OpenAI | Confirm the zsh function is loaded (`type codex`) and `CODEX_BACKEND=local` is set in current session. New terminals need explicit export. |
| Streaming or tool calls fail | Validate Responses streaming and tool-call compatibility. A simple text response success does not guarantee full API parity. |
| Local responses are slow (~4 min) | Check `ollama ps`, model swapping, context length, and whether TEV is invoked repeatedly. Review LiteLLM logs for retries and timeouts. Consider reducing `request_timeout` if delay is from the router. |
| CAPTCHA on Gemini Search | Open http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale in a browser and complete the challenge manually. |
| Container startup fails (Apple Silicon) | Use `linux/amd64` build for Docker Compose on M-series Macs. ARM64 wheels may crash with illegal instruction errors. |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Codex CLI 0.163.0                                   │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
                   │ CODEX_BACKEND env var
                   ▼
        ┌─────────────────────────────┐
        │   Session Variable Check    │
        │  (CODEX_BACKEND: openai)    │
        └────┬────────────────────────┘
              │
        ┌─────┴─────┐
        │           │
        ▼           ▼
┌──────────────┐  ┌──────────────────┐
│  OpenAI      │  │  LiteLLM         │
│  Backend     │  │  Gateway:4000    │
│              │  └────────┬─────────┘
└──────────────┘           │
                           ▼
                 ┌─────────────────────────────┐
                 │   Complexity Router         │
                 │   (engineering-auto)        │
                 │   TEV1:0.8b classifier      │
                 └────────┬────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
            ▼                           ▼
    ┌───────────────┐         ┌───────────────────┐
    │   Qwen3.5     │         │  DeepSeek-R1      │
    │   (CODE/ARCH) │         │   (REASONING)     │
    │               │         │                   │
    └───────┬───────┘         └───────────────────┘
            │
            ▼
    Ollama Qwen3.5:latest (mlx on GPU)

┌─────────────────────────────────────────────────────────────────────────────┐
│                    Gemini Search MCP                                        │
└──────────────────┬──────────────────────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │ docker compose      │
        │   gemini-search    │
        └────┬────────────────┘
              ▼
    ┌─────────────────────────┐
    │ Chromium (amd64)        │
    │ MCP:3000/http           │
    │ noVNC:6080/vnc          │
    └───────┬─────────────────┘
            │
            ▼
   Google AI Mode + Browser Automation
```

---

## Quick Reference

### Ollama Commands

| Command | Result |
|---------|--------|
| `ollama pull Qwen3.5:latest` | Download coding model (~7.7 GB) |
| `ollama pull deepseek-r1:8b` | Download reasoning model (~8 GB) |
| `ollama pull tev1:0.8b` | Download TEV classifier (~1 GB) |
| `ollama list` | List all pulled models |
| `launchctl setenv OLLAMA_CONTEXT_LENGTH 8192` | Set default context window |
| `osascript -e 'quit app "Ollama"'` | Quit Ollama desktop app |
| `open -a Ollama` | Launch Ollama |
| `ollama ps` | Show active models and runtime allocations |

### LiteLLM Commands

| Command | Result |
|---------|--------|
| `export LITELLM_API_KEY=xxx` | Set API key for session |
| `curl http://localhost:4000/health/liveliness` | Check gateway health |
| `curl http://localhost:4000/v1/models -H "Authorization: Bearer xxx"` | List model aliases |
| `docker compose up -d litellm` | Start LiteLLM gateway |
| `docker compose logs --tail=150 litellm` | View recent gateway logs |

### Codex Commands

| Command | Result |
|---------|--------|
| `codex --version` | Check CLI version (expected 0.163.0) |
| `codex` | Default OpenAI backend (or `CODEX_BACKEND` if set) |
| `CODEX_BACKEND=local codex` | Use LiteLLM for single command |
| `export CODEX_BACKEND=local` | Make local the default in current shell |
| `command codex --profile local` | Explicitly select local profile (bypasses wrapper) |
| `codex exec 'your prompt'` | Run Codex exec mode |

### Gemini Search Commands

| Command | Result |
|---------|--------|
| `docker compose build gemini-search` | Build the MCP container image |
| `docker compose up -d --build gemini-search` | Start persistent service |
| `docker compose ps gemini-search` | Verify container status |
| `codex --profile local` | Start Codex with MCP + LiteLLM |

---

## Important Notes

1. **Model Names:** Case-sensitive. Match exactly what `ollama list` returns (e.g., `Qwen3.5:latest` not `qwen3.5`).

2. **Context Window:** `OLLAMA_CONTEXT_LENGTH=8192` is a server-side default that requires a full Ollama restart to apply. Use `ollama ps` to verify actual allocations.

3. **Responses API Required:** Codex CLI uses the OpenAI Responses API, not Chat Completions. Your LiteLLM gateway must support `/v1/responses` with streaming and tool calls.

4. **TEV Routing is Not Automatic:** The Codex profile alone does not enable semantic routing. TEV routing depends on the deployed LiteLLM configuration and its compatibility with Ollama's System One API.

5. **No Duplicate TOML Tables:** When editing `~/.codex/config.toml`, merge existing `[model_providers.litellm]` and `[profiles.local]` entries rather than creating duplicates.

6. **Secrets Management:** Never commit `.env` files or real API keys to source control. Use `git checkout` to restore if accidentally committed.

7. **Apple Silicon Compatibility:** Docker Desktop runs containers in emulation on M-series Macs. Use `linux/amd64` for Docker Compose services. Browser automation will be slower than native ARM64 builds.

8. **Memory Usage Fluctuates:** Download sizes ≠ runtime allocations. `ollama ps` shows actual GPU/CPU usage and context window per model.

---

## Appendix: Sample config.yaml (Project-Based Setup)

```yaml
model_list:
  - model_name: qwen-coder
    litellm_params:
      model: ollama_chat/Qwen3.5:latest
      api_base: http://host.docker.internal:11434
      api_key: ollama
    model_info:
      max_input_tokens: 262144

  - model_name: deepseek-reasoner
    litellm_params:
      model: ollama_chat/deepseek-r1:8b
      api_base: http://host.docker.internal:11434
      api_key: ollama
    model_info:
      max_input_tokens: 131072

  - model_name: engineering-auto
    litellm_params:
      model: auto_router/complexity_router
      complexity_router_config:
        context_compaction: false
        tiers:
          SIMPLE: qwen-coder
          MEDIUM: qwen-coder
          COMPLEX: qwen-coder
          REASONING: deepseek-reasoner
        classifier_type: jev
        jev_classifier_config:
          model: tev1:0.8b
          api_base: http://host.docker.internal:11434
          api_key: ollama
          timeout_ms: 15000
          circuit_breaker_enabled: true
          circuit_breaker_cooldown_seconds: 30
        classifier_fallback: heuristic
        classifier_context_window_size: 1
        classifier_context_budget_chars: 1000
        classification_mode: user_turn
        session_affinity: true
        session_affinity_ttl_seconds: 3600
        custom_technical_keywords:
          - spring
          - maven
          - java
          - react
          - kafka
          - postgres
          - concurrency
          - deadlock
      complexity_router_default_model: qwen-coder

litellm_settings:
  num_retries: 1
  request_timeout: 240
  drop_params: true

router_settings:
  set_verbose: true

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

---

*Last updated: 2026-10-21*
