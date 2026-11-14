# LiteLLM + TEV on Ollama

## LiteLLM Ollama tool-call compatibility

Compose builds `litellm-ollama-tools:1.106.1` from the pinned upstream LiteLLM
image. A checked source patch preserves Ollama's streamed tool-call indices and
IDs so separate calls are not concatenated into invalid JSON on a later
Responses API continuation. The build fails if the upstream version or expected
source changes; review or remove the patch when upgrading LiteLLM.

```bash
docker compose up -d --build --no-deps litellm
docker compose exec -T litellm /app/.venv/bin/python - < litellm/test_ollama_streaming.py
docker compose exec -T litellm /app/.venv/bin/python - < litellm/smoke_tool_roundtrip.py
```

Start a new client conversation after deploying this fix if its history already
contains concatenated tool arguments. The patch prevents future corruption; it
does not rewrite client history or guess how to repair malformed JSON.

## Headroom compression

LiteLLM calls Headroom at `http://headroom:8787` before model requests using the
default-on `headroom-compression` guardrail. Headroom is internal to the Compose
network, and LiteLLM waits for its readiness check before starting.

The Headroom service sets `OPENSSL_armcap=0` to avoid an illegal-instruction
crash (exit code 132) in cryptography/OpenSSL on Apple Silicon Docker VMs.
This disables OpenSSL's ARM hardware acceleration in that container.

```bash
docker compose up -d --wait headroom litellm
```

## Local skills MCP server

The Poetry-managed `skills-mcp` service uses FastMCP 4 to expose skills from
`~/.skills` over HTTP at `http://127.0.0.1:8001/mcp`.
It provides `list_skills` (ids and relative paths for recursive `SKILL.md` files)
and `get_skill(skill_id)` (the full instructions for a listed id).
Files are read on each request, so edits appear without restarting the service.

```bash
mkdir -p ~/.skills
docker compose up -d --build skills-mcp
```

The directory is mounted read-only. Skill files must be readable by the
container's non-root user; symlinks outside the mounted directory are excluded.
Other Compose services can connect to `http://skills-mcp:8001/mcp`.

For local development:

```bash
cd skills-mcp
poetry install
poetry run skills-mcp
```

Set `SKILLS_DIR` to override `~/.skills` when running locally.

## Requirements
- Docker Compose on macOS
- Ollama 0.35+ running on the Mac host
- `ollama list` includes `Qwen3.5:latest`, `deepseek-r1:8b`, `tev1:0.8b`

## Setup
```bash
cp .env.example .env
# Replace the master key with a secret: echo "LITELLM_MASTER_KEY=sk-$(openssl rand -hex 32)" > .env
chmod 600 .env
docker compose up -d
docker compose logs -f litellm
```

Test host Ollama from Docker:
```bash
docker run --rm curlimages/curl:latest -fsS http://host.docker.internal:11434/api/tags
```

Test TEV on host:
```bash
curl -sS http://localhost:11434/v1/systemone -H 'Content-Type: application/json' -d '{"model":"tev1:0.8b","state":"Investigate a Java deadlock","questions":{"tier":{"type":"choice","instructions":"Choose task complexity","criteria":{"SIMPLE":"Trivial","MEDIUM":"Moderate","COMPLEX":"Complex engineering","REASONING":"Deep reasoning"}}}}'
```

Test LiteLLM:
```bash
set -a; source .env; set +a
curl -sS http://localhost:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' -d '{"model":"engineering-auto","messages":[{"role":"user","content":"Analyze a complex Java concurrency deadlock"}],"stream":false}'
```

## Important
- The LiteLLM JEV classifier's use of a local TEV endpoint is an API-compatible integration candidate, not a verified supported pairing. Check logs for `cause=jev_classifier` (or classifier failure/fallback), and confirm it actually selected a tier.
- The `main-stable` tag is a moving tag. Pin a tested image digest for production.
- `session_affinity` requires a stable session ID in request metadata; without it, the model can be reclassified each turn.
- On macOS, host.docker.internal is the correct Docker Desktop hostname. Ollama may need to bind to 0.0.0.0:11434 for container access; only do so on a trusted machine and avoid exposing port 11434 publicly.
- When `OLLAMA_MAX_LOADED_MODELS=1`, TEV and Qwen/DeepSeek will swap, potentially adding latency.
