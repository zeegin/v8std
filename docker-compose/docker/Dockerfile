FROM python:3.12-slim

WORKDIR /tmp

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cargo fonts-dejavu-core git rustc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
COPY scripts /tmp/scripts

RUN chmod +x /tmp/scripts/generate_social_cards.py /tmp/scripts/install_zensical.sh /tmp/scripts/zensical_docs.sh \
    && /tmp/scripts/install_zensical.sh

WORKDIR /docs

ENTRYPOINT ["/tmp/scripts/zensical_docs.sh"]
CMD ["serve", "--dev-addr=0.0.0.0:8000"]
