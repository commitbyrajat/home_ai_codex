FROM docker.litellm.ai/berriai/litellm:1.106.1

COPY patch_ollama.py /app/compat/patch_ollama.py
RUN /app/.venv/bin/python /app/compat/patch_ollama.py
