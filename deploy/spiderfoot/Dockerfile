# SpiderFoot v4.0 on a current Python. Upstream's Dockerfile builds on Alpine 3.12, where its
# pinned requirements (notably pyyaml<6) no longer compile. Source is the unmodified upstream tag;
# the only change is relaxing the pyyaml pin so a prebuilt wheel is used.
FROM python:3.11-slim

ARG SPIDERFOOT_REF=v4.0
ADD https://github.com/smicallef/spiderfoot.git#${SPIDERFOOT_REF} /opt/spiderfoot
WORKDIR /opt/spiderfoot

RUN apt-get update \
    && apt-get install -y --no-install-recommends libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i 's/^pyyaml.*/pyyaml>=5.4.1,<7/I' requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

ENV SPIDERFOOT_DATA=/var/lib/spiderfoot \
    SPIDERFOOT_LOGS=/var/lib/spiderfoot/log \
    SPIDERFOOT_CACHE=/var/lib/spiderfoot/cache

RUN useradd --system --home-dir /home/spiderfoot --create-home spiderfoot \
    && mkdir -p "$SPIDERFOOT_DATA" "$SPIDERFOOT_LOGS" "$SPIDERFOOT_CACHE" \
    && chown -R spiderfoot:spiderfoot "$SPIDERFOOT_DATA"
USER spiderfoot

EXPOSE 5001
CMD ["python", "sf.py", "-l", "0.0.0.0:5001"]
