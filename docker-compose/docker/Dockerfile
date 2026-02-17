FROM squidfunk/mkdocs-material:latest

WORKDIR /tmp/build

COPY requirements.txt /tmp/build/requirements.txt

RUN pip install --no-cache-dir -r /tmp/build/requirements.txt
