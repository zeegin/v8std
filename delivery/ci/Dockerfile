# Public artifact builder only. Tests run on the host with Docker CLI available.
# The immutable Python base also pins libc/zlib/gzip implementation and pip.
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements-build.lock /opt/v8std/requirements-build.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /opt/v8std/requirements-build.lock \
    && python -m pip check
# Same DejaVu public social-card family; no apt resolver or fallback font.
ADD --checksum=sha256:86635b3d25b3655fc11cb3ecc3af59f0bf19643b02b94f2de48bd10253cdba12 https://deb.debian.org/debian/pool/main/f/fonts-dejavu/fonts-dejavu-core_2.37-8_all.deb /opt/v8std/fonts.deb
RUN dpkg-deb --extract /opt/v8std/fonts.deb / \
    && test -s /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf \
    && test -s /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    && rm /opt/v8std/fonts.deb
WORKDIR /docs
USER 10001:10001
ENTRYPOINT ["bash", "scripts/zensical_docs.sh"]
