"""Apply a checked, version-specific fix for Ollama streamed tool indices."""

from importlib.metadata import version
from pathlib import Path


def patch() -> None:
    if version("litellm") != "1.106.1":
        raise RuntimeError("Review the Ollama compatibility patch before upgrading LiteLLM")
    import litellm.llms.ollama.chat.transformation as transformation

    path = Path(transformation.__file__)
    source = path.read_text()
    old = '''                for tool_call in tool_calls:
                    function_args = tool_call.get("function").get("arguments")
                    if function_args is not None and len(function_args) > 0:
                        is_function_call_complete = self._is_function_call_complete(function_args)
                        if is_function_call_complete:
                            tool_call["id"] = str(uuid.uuid4())
'''
    new = '''                for tool_call in tool_calls:
                    # Ollama places the index inside function; Chat Completions
                    # requires it on tool_call. Without it, all calls become 0
                    # and stream_chunk_builder concatenates their JSON objects.
                    function = tool_call.get("function") or {}
                    provider_index = tool_call.get("index", function.get("index"))
                    identities = self.__dict__.setdefault("_ollama_tool_identities", {})
                    if provider_index is not None:
                        identity = ("index", provider_index)
                    elif tool_call.get("id"):
                        identity = ("id", tool_call["id"])
                    else:
                        # Older Ollama versions emit complete calls without ids
                        # or indices. Each such object is a separate call.
                        identity = ("anonymous", len(identities))
                    if identity not in identities:
                        identities[identity] = (len(identities), tool_call.get("id") or str(uuid.uuid4()))
                    tool_call["index"], tool_call["id"] = identities[identity]
'''
    if source.count(old) != 1:
        raise RuntimeError("Unexpected Ollama stream parser source; refusing to patch")
    path.write_text(source.replace(old, new, 1))
    print("Applied Ollama streamed tool-call index fix for LiteLLM 1.106.1")


if __name__ == "__main__":
    patch()
