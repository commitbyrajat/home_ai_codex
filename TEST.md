# Verify JEV Routing

These requests verify that LiteLLM's `engineering-auto` router calls the configured TEV/JEV classifier and records the selected tier. Set `LITELLM_MASTER_KEY` in `.env` first.

```bash
set -a
source .env
set +a
```

## 1. Classify without running a completion

`/auto_router/test_routing` runs the classifier and returns the routing decision without sending the request to Qwen or DeepSeek.

```bash
curl -fsS http://localhost:4000/auto_router/test_routing \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON' | jq .
{
  "prompt": "A Java service deadlocks under load: one thread holds the account lock and waits for inventory, while another holds inventory and waits for account. Identify the root cause and choose a complexity tier.",
  "default_model": "qwen-coder",
  "router_name": "engineering-auto",
  "complexity_router_config": {
    "tiers": {
      "SIMPLE": "qwen-coder",
      "MEDIUM": "qwen-coder",
      "COMPLEX": "qwen-coder",
      "REASONING": "deepseek-reasoner"
    },
    "classifier_type": "jev",
    "jev_classifier_config": {
      "model": "tev1:0.8b",
      "api_base": "http://host.docker.internal:11434",
      "api_key": "ollama",
      "timeout_ms": 15000,
      "circuit_breaker_enabled": true,
      "circuit_breaker_cooldown_seconds": 30
    },
    "classifier_fallback": "heuristic",
    "classifier_context_window_size": 1,
    "classifier_context_budget_chars": 1000,
    "classification_mode": "user_turn",
    "session_affinity": true,
    "session_affinity_ttl_seconds": 3600,
    "context_compaction": false,
    "custom_technical_keywords": [
      "spring", "maven", "java", "react", "kafka", "postgres", "concurrency", "deadlock"
    ]
  }
}
JSON
```

JEV is confirmed when `routing_decision.cause` is `jev_classifier`. The response should also include a `tier`, `classifier_model`, `classifier_probabilities`, and `classifier_confidence`. A different cause means the request fell back or was routed by another path.

To make the command fail unless JEV classified the request, replace `| jq .` with:

```bash
| jq -e '.routing_decision | select(.cause == "jev_classifier" and .tier != null and .classifier_probabilities != null)'
```

## 2. Run a completion and inspect routing logs

Use a fresh session ID so `session_affinity` cannot reuse an earlier decision:

```bash
SESSION_ID="jev-smoke-$(date +%s)"

curl -fsS http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON
{
  "model": "engineering-auto",
  "messages": [{
    "role": "user",
    "content": "A Java service deadlocks under load: one thread holds the account lock and waits for inventory, while another holds inventory and waits for account. Explain the cause and recommend a safe fix."
  }],
  "stream": false,
  "metadata": {"session_id": "$SESSION_ID"}
}
JSON
```

Then inspect the router decision written to the LiteLLM container logs:

```bash
docker compose logs --since=2m litellm | grep -F 'ComplexityRouter: routing decision'
```

For a successful JEV classification, the line includes `cause=jev_classifier`, the chosen `tier`, classifier confidence/probability signals, and `routed_model`. A heuristic/fallback cause indicates that JEV did not supply the decision; check the surrounding log lines and confirm the host Ollama service has `tev1:0.8b` available.

The log verbosity is enabled by `router_settings.set_verbose` in `config.yaml`. Logs are emitted to Docker stdout and can be followed with `docker compose logs -f litellm`.

## 3. Example aimed at the DeepSeek tier

This theoretical proof request was classified as `REASONING` by the configured JEV model, which maps to `deepseek-reasoner`. JEV makes a classification decision, so confirm the selected model in the log after each request.

```bash
SESSION_ID="jev-deepseek-$(date +%s)"

curl -fsS http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON
{
  "model": "engineering-auto",
  "messages": [{
    "role": "user",
    "content": "This is a deep reasoning task, not implementation work: analyze whether P equals NP, state what is known, and construct a rigorous proof. If a proof cannot be supplied, explain the precise obstacle and distinguish established results from conjecture."
  }],
  "max_tokens": 128,
  "stream": false,
  "metadata": {"session_id": "$SESSION_ID"}
}
JSON
```

Confirm that the log reports both `tier=REASONING` and `routed_model=deepseek-reasoner`:

```bash
docker compose logs --since=2m litellm | grep -F 'ComplexityRouter: routing decision'
```
