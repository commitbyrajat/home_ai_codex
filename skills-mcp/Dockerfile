FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir poetry==2.4.1
# Match the stack's ARM OpenSSL workaround for Docker Desktop.
ENV POETRY_VIRTUALENVS_IN_PROJECT=true OPENSSL_armcap=0
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-interaction
COPY skills_mcp ./skills_mcp
RUN poetry install --only-root --no-interaction

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 SKILLS_DIR=/skills OPENSSL_armcap=0
USER 10001:10001
EXPOSE 8001
CMD ["skills-mcp"]
