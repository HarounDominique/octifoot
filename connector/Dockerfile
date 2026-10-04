FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/connector
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --system --no-create-home connector
USER connector

ENTRYPOINT ["python", "-m", "spiderfoot_connector"]
