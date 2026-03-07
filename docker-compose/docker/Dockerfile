FROM python:3.12-slim

WORKDIR /tmp

ENV PATH="/root/.cargo/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates curl fonts-dejavu-core git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
COPY scripts /tmp/scripts

RUN chmod +x /tmp/scripts/generate_social_cards.py /tmp/scripts/install_zensical.sh /tmp/scripts/zensical_docs.sh \
    && . /tmp/scripts/zensical-version.sh \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --default-toolchain "${ZENSICAL_RUST_VERSION}" \
    && /tmp/scripts/install_zensical.sh

WORKDIR /docs

ENTRYPOINT ["/tmp/scripts/zensical_docs.sh"]
CMD ["serve", "--dev-addr=0.0.0.0:8000"]
