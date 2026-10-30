# Sandbox image for CI, evals and optional local runs: pinned GAMS + gams-tools, no license baked in.
#
# Build (installer from an internal mirror recommended):
#   docker build --build-arg GAMS_VERSION=53.5.1 --build-arg GAMS_INSTALLER_URL=https://mirror/.../linux_x64_64_sfx.exe \
#                -t gams-sme-sandbox:53.5.1 -f sandbox/Dockerfile .
# Run with no network, the repository read-only, and the license mounted at runtime:
#   docker run --rm --network none \
#     -v "$PWD":/work:ro -v "$PWD/.gams-agent":/work/.gams-agent \
#     -v /secure/gamslice.txt:/run/secrets/gamslice.txt:ro \
#     gams-sme-sandbox:53.5.1 check
FROM python:3.12-slim

ARG GAMS_VERSION=53.5.1
ARG GAMS_INSTALLER_URL=""

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install GAMS: the official installer when a URL is given, otherwise the GAMS system in the
# gamspy-base wheel of the same version (confirm this is acceptable under your GAMS license).
RUN set -eux; \
    if [ -n "$GAMS_INSTALLER_URL" ]; then \
      mkdir -p /opt/gams && cd /opt/gams && curl -fsSL -o installer.exe "$GAMS_INSTALLER_URL" \
      && chmod +x installer.exe && ./installer.exe > /dev/null && rm installer.exe \
      && ln -s "$(ls -d /opt/gams/gams*_linux_x64_64_sfx | head -1)" /opt/gams/current; \
    else \
      pip install --no-cache-dir --target /opt/gamsbase "gamspy-base==${GAMS_VERSION}" \
      && mkdir -p /opt/gams && ln -s /opt/gamsbase/gamspy_base /opt/gams/current; \
    fi

ENV GAMS_SYSDIR=/opt/gams/current \
    PATH=/opt/gams/current:$PATH

COPY mcp/gams-tools /src/gams-tools
RUN pip install --no-cache-dir "/src/gams-tools[mcp]"

# The license is mounted at /run/secrets/gamslice.txt and linked into the system directory at start.
RUN printf '#!/bin/sh\nset -e\nif [ -f /run/secrets/gamslice.txt ]; then ln -sf /run/secrets/gamslice.txt "$GAMS_SYSDIR/gamslice.txt"; fi\nexec gams-tools "$@"\n' \
      > /usr/local/bin/entrypoint && chmod +x /usr/local/bin/entrypoint \
    && useradd --create-home --uid 10001 gams && chown -R gams /opt/gams/current/

USER gams
WORKDIR /work
ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["--help"]
