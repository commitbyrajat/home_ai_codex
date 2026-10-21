# LiteLLM + TEV on Ollama

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
