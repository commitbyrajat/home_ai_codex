FROM python:3.12-slim

ARG GEMINI_SEARCH_REF=892a5ab4e7f9d61c5c12a8dfbf4946c5b6ba1aa7

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git ca-certificates xvfb x11vnc novnc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/gemini-search
RUN git init . \
    && git remote add origin https://github.com/Sophomoresty/gemini-search-mcp.git \
    && git fetch --depth 1 origin "${GEMINI_SEARCH_REF}" \
    && git checkout --detach FETCH_HEAD

# Install the standalone FastMCP 4 server SDK. The upstream project depends on
# the lower-level MCP SDK, but its bundled FastMCP server is not used here.
RUN pip install --no-cache-dir -e . playwright 'fastmcp>=4,<5' \
    && playwright install chromium --with-deps \
    && rm -rf /var/lib/apt/lists/*

COPY http_server.py /opt/gemini-search/http_server.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "/opt/gemini-search/http_server.py"]
