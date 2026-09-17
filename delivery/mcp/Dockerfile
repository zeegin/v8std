FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
ARG SOURCE_SHA
LABEL org.opencontainers.image.title="v8std MCP" \
      org.opencontainers.image.source="https://github.com/zeegin/v8std" \
      org.opencontainers.image.revision="${SOURCE_SHA}" \
      org.opencontainers.image.licenses="CC0-1.0"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    V8STD_MCP_CACHE_DIR=/var/lib/v8std-mcp V8STD_MCP_RUNTIME_SHA=${SOURCE_SHA}
WORKDIR /opt/v8std
COPY runtime/requirements-mcp.lock ./runtime/
RUN python -c 'import os,re; assert re.fullmatch("[0-9a-f]{40}",os.environ["V8STD_MCP_RUNTIME_SHA"])' \
    && python -m pip install --no-cache-dir --require-hashes -r runtime/requirements-mcp.lock \
    && python -m pip check \
    && mkdir -p /var/lib/v8std-mcp \
    && chown 10001:10001 /var/lib/v8std-mcp
COPY runtime/__init__.py runtime/v8std_mcp_server.py runtime/v8std_mcp_runtime.py runtime/v8std_mcp_index.py \
     runtime/v8std_mcp_snapshots.py runtime/v8std_mcp_snapshot_format.py runtime/v8std_mcp_hold.py \
     runtime/v8std_mcp_presentation.py ./runtime/
COPY scripts/v8std_mcp_chunks.py scripts/v8std_retrieval_rules.py scripts/v8std_search_features.py ./scripts/
COPY retrieval-rules.yml LICENSE ./
COPY LICENSES ./LICENSES/
USER 10001:10001
ENTRYPOINT ["python", "-m", "runtime.v8std_mcp_server"]
EXPOSE 8000
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
