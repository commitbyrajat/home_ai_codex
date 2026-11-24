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

## BGE reranking for LightRAG

The `memory-rerank` alias serves `qllama/bge-reranker-v2-m3:latest` through
LiteLLM's `/v1/rerank` endpoint. The `reranker` Compose service uses the official
prebuilt llama.cpp server image, pinned by digest, and mounts the GGUF already
downloaded by Ollama read-only. No image build or additional model download is
needed. Ollama continues serving chat and embeddings; llama.cpp serves reranking
on the internal Compose network using CPU inference.

LiteLLM uses the `cohere/` provider for the local server's compatible API format.
All reranking requests stay local, and both services authenticate with
`LITELLM_MASTER_KEY`. LiteLLM waits for the reranker's health check at startup.

The default model file matches Ollama manifest `06e0e64a6f61`. For a different
Ollama model directory or updated model layer, set `BGE_RERANK_MODEL_PATH` in
`.env` to the absolute GGUF/blob path. `ollama show --modelfile
qllama/bge-reranker-v2-m3:latest` shows the model's `FROM` path. The bind mount
fails if the file does not exist. The configured query/document pair limit is
4096 model tokens; split longer documents before reranking.

Start the server and apply the proxy configuration without building images:

```bash
docker compose up -d --no-build --wait reranker litellm
docker compose restart litellm
```

Test the same request format LightRAG uses:

```bash
set -a; source .env; set +a
curl --fail-with-body -sS http://localhost:4000/v1/rerank \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "memory-rerank",
    "query": "What is the capital of France?",
    "documents": ["Bananas are yellow.", "Paris is the capital of France."],
    "top_n": 1
  }'
```

The response's `results` array contains original document indices and
`relevance_score` values, sorted by relevance. No chat prompt or response parsing
adapter is required. This BGE GGUF returns raw relevance logits, which can be
negative or greater than 1. Keep LightRAG's `MIN_RERANK_SCORE=0.0` to disable
threshold filtering; probability-based thresholds do not apply to these scores.

For a LightRAG container attached to this stack's Compose network, configure:

```dotenv
RERANK_BINDING=cohere
RERANK_MODEL=memory-rerank
RERANK_BINDING_HOST=http://litellm:4000/v1/rerank
RERANK_BINDING_API_KEY=<same value as LITELLM_MASTER_KEY>
RERANK_TIMEOUT=120
MAX_ASYNC_RERANK=1
MIN_RERANK_SCORE=0.0
```

Join the LightRAG container to this stack's network in its Compose configuration
(the default name is `litellm-tev-stack_default`). The `litellm` hostname is only
available on that network. These settings belong in LightRAG's environment;
restart/recreate its container after applying them. This does not automatically
change Graphiti's search behavior.

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
