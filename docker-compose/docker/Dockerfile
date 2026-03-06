FROM python:3.12-slim

WORKDIR /tmp

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cargo git rustc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
COPY scripts /tmp/scripts

RUN chmod +x /tmp/scripts/install_zensical.sh \
    && /tmp/scripts/install_zensical.sh

WORKDIR /docs

ENTRYPOINT ["zensical"]
CMD ["serve", "--dev-addr=0.0.0.0:8000"]
