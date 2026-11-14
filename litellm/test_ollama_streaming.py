"""Run inside the patched image using unittest or stdin."""

import json
import unittest
from types import SimpleNamespace

from litellm.llms.ollama.chat.transformation import (
    OllamaChatCompletionResponseIterator,
    OllamaChatConfig,
)
from litellm.main import stream_chunk_builder
from litellm.responses.litellm_completion_transformation.streaming_iterator import LiteLLMCompletionStreamingIterator


def native_call(name, arguments, index=None, call_id=None):
    function = {"name": name, "arguments": arguments}
    if index is not None:
        function["index"] = index
    call = {"function": function}
    if call_id is not None:
        call["id"] = call_id
    return call


def parsed_chunks(groups):
    parser = OllamaChatCompletionResponseIterator(streaming_response=iter([]), sync_stream=True)
    chunks = []
    for calls in groups:
        chunks.append(parser.chunk_parser({
            "model": "test", "message": {"role": "assistant", "content": "", "tool_calls": calls}, "done": False,
        }))
    chunks.append(parser.chunk_parser({
        "model": "test", "message": {"role": "assistant", "content": ""},
        "done": True, "done_reason": "stop", "prompt_eval_count": 1, "eval_count": 1,
    }))
    return chunks


def assemble(groups):
    return stream_chunk_builder(parsed_chunks(groups))


class OllamaStreamingTests(unittest.TestCase):
    def test_empty_call_and_search_call_remain_separate(self):
        response = assemble([
            [native_call("web_search", {}, 0, "call_empty")],
            [native_call("web_search", {"query": "hello"}, 1, "call_search")],
        ])
        calls = response.choices[0].message.tool_calls
        self.assertEqual([c.id for c in calls], ["call_empty", "call_search"])
        self.assertEqual([json.loads(c.function.arguments) for c in calls], [{}, {"query": "hello"}])
        # A continuation must serialize both calls back to native Ollama objects.
        messages = [response.choices[0].message.model_dump(exclude_none=True)]
        request = OllamaChatConfig().transform_request("test", messages, {}, {}, {})
        self.assertEqual([c["function"]["arguments"] for c in request["messages"][0]["tool_calls"]], [{}, {"query": "hello"}])

    def test_same_named_calls_with_different_arguments(self):
        response = assemble([
            [native_call("get_skill", {"skill_id": "coding-workflow"}, 0, "call_a")],
            [native_call("get_skill", {"skill_id": "springboot-project-generator"}, 1, "call_b")],
        ])
        self.assertEqual([json.loads(c.function.arguments)["skill_id"] for c in response.choices[0].message.tool_calls], ["coding-workflow", "springboot-project-generator"])

    def test_multiple_calls_in_one_chunk_without_indices_or_ids(self):
        response = assemble([[native_call("echo", {"query": "alpha"}), native_call("echo", {"query": "beta"})]])
        calls = response.choices[0].message.tool_calls
        self.assertEqual(len({c.id for c in calls}), 2)
        self.assertEqual([json.loads(c.function.arguments) for c in calls], [{"query": "alpha"}, {"query": "beta"}])

    def test_single_empty_call_is_preserved(self):
        response = assemble([[native_call("list_skills", {}, 0, "call_list")]])
        calls = response.choices[0].message.tool_calls
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].id, "call_list")
        self.assertEqual(json.loads(calls[0].function.arguments), {})

    def test_responses_stream_deltas_match_final_call_arguments(self):
        chunks = parsed_chunks([
            [native_call("echo", {"query": "alpha"}, 0, "call_a")],
            [native_call("echo", {"query": "beta"}, 1, "call_b")],
        ])
        bridge = LiteLLMCompletionStreamingIterator(
            model="test", litellm_custom_stream_wrapper=SimpleNamespace(logging_obj=None),
            request_input="", responses_api_request={}, custom_llm_provider="ollama_chat",
        )
        for chunk in chunks:
            bridge._queue_tool_call_delta_events(chunk.choices[0].delta.tool_calls)
        bridge._queue_final_tool_call_done_events(stream_chunk_builder(chunks))
        deltas, completed = {}, {}
        for event in bridge._pending_tool_events:
            if event.type == "response.function_call_arguments.delta":
                deltas[event.item_id] = deltas.get(event.item_id, "") + event.delta
            elif event.type == "response.output_item.done":
                completed[event.item.id] = event.item.arguments
        self.assertEqual(deltas, completed)
        self.assertEqual([json.loads(value) for value in completed.values()], [{"query": "alpha"}, {"query": "beta"}])

    def test_malformed_history_is_not_silently_repaired(self):
        messages = [{"role": "assistant", "tool_calls": [{"type": "function", "id": "bad", "function": {"name": "echo", "arguments": '{}{"query":"hello"}'}}]}]
        with self.assertRaises(json.JSONDecodeError):
            OllamaChatConfig().transform_request("test", messages, {}, {}, {})


if __name__ == "__main__":
    unittest.main()
