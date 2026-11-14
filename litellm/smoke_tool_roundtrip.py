"""Synthetic live Responses API tool round trip; run inside the proxy container."""

import json
import os
import time
import urllib.request

BASE_URL = "http://127.0.0.1:4000"


def responses(body):
    request = urllib.request.Request(
        BASE_URL + "/v1/responses", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["LITELLM_MASTER_KEY"]},
    )
    deltas = {}
    completed = None
    with urllib.request.urlopen(request, timeout=180) as response:
        for line in response:
            if not line.startswith(b"data: ") or line[6:].strip() == b"[DONE]":
                continue
            event = json.loads(line[6:])
            if event.get("type") in ("error", "response.failed") or event.get("error"):
                raise RuntimeError("Responses stream returned an error")
            if event.get("type") == "response.function_call_arguments.delta":
                key = event["item_id"]
                deltas[key] = deltas.get(key, "") + event["delta"]
            if event.get("type") == "response.completed":
                completed = event["response"]
    assert completed is not None, "Missing response.completed event"
    return completed, deltas


def main():
    for attempt in range(60):
        try:
            with urllib.request.urlopen(BASE_URL + "/health/liveliness", timeout=2):
                break
        except OSError:
            if attempt == 59:
                raise
            time.sleep(1)

    prompt = "Call echo twice: once with query alpha and once with query beta. Make both tool calls now. Do not answer in text."
    tools = [{"type": "function", "name": "echo", "description": "Echo a query.", "parameters": {
        "type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"],
    }}]
    history = [{"role": "user", "content": prompt}]
    initial, deltas = responses({"model": "engineering-auto", "input": history, "tools": tools, "stream": True, "max_output_tokens": 256})
    calls = [item for item in initial["output"] if item["type"] == "function_call"]
    assert len(calls) == 2, f"Expected two synthetic tool calls; got {len(calls)}"
    assert len({item["call_id"] for item in calls}) == 2, "Merged call ids"
    queries = []
    for call in calls:
        assert deltas[call["id"]] == call["arguments"], "Streamed arguments differ from completed output"
        args = json.loads(call["arguments"])
        queries.append(args["query"])
    assert sorted(queries) == ["alpha", "beta"], "Incorrect synthetic tool arguments"
    print("PASS: two distinct streamed tool calls with valid JSON", flush=True)
    history.extend(initial["output"])
    history.extend({"type": "function_call_output", "call_id": call["call_id"], "output": json.dumps({"echo": query})} for call, query in zip(calls, queries))
    history.append({"role": "user", "content": "Both calls succeeded. Reply with a brief confirmation. Do not call any tools."})
    final, _ = responses({"model": "engineering-auto", "input": history, "tools": tools, "stream": True, "max_output_tokens": 128})
    assert final["status"] == "completed", "Continuation did not complete"
    assert any(item["type"] == "message" for item in final["output"]), "Expected assistant confirmation"
    print("PASS: engineering-auto continuation with both tool outputs", flush=True)


if __name__ == "__main__":
    main()
