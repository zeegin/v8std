FROM python:3.12-slim

WORKDIR /tmp

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
COPY requirements-mcp.txt /tmp/requirements-mcp.txt
COPY scripts /tmp/scripts

RUN chmod +x /tmp/scripts/generate_social_cards.py \
    /tmp/scripts/generate_search_vectors.py \
    /tmp/scripts/install_zensical.sh \
    /tmp/scripts/run_v8std_mcp.sh \
    /tmp/scripts/v8std_mcp_server.py \
    /tmp/scripts/zensical_docs.sh \
    && /tmp/scripts/install_zensical.sh \
    && python -m pip install --upgrade -r /tmp/requirements-mcp.txt

WORKDIR /docs

ENTRYPOINT ["/tmp/scripts/zensical_docs.sh"]
CMD ["serve", "--dev-addr=0.0.0.0:8000"]
