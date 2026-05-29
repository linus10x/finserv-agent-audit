# Reference Dockerfile for the finserv-agent-audit Kubernetes operator stub.
#
# This image is REFERENCE-ONLY. Production deployers should rebuild on top of
# operator-sdk or kopf rather than the stdlib stub controller. The image
# exists so the deploy/k8s/README.md walkthrough can be followed end-to-end
# in a kind / minikube / dev cluster without bespoke build steps.
#
# Hardening posture v2.0:
#   * Multi-stage build — final image carries no build toolchain.
#   * Base pinned by digest, not floating tag — supply-chain pinning.
#   * Non-root UID (65532, distroless "nonroot" convention).
#   * Read-only root filesystem assumed (enforced via Deployment securityContext).
#   * Distroless variant fallback: production deployers SHOULD swap the
#     final stage to gcr.io/distroless/python3-debian12:nonroot once the
#     wheel install path is wired through `pip install --target=` in the
#     builder. The reference stub uses python:3.13-slim-bookworm in the
#     final stage because distroless lacks pip and the framework wheel
#     requires `pip install` to populate site-packages. The gap is
#     documented in deploy/k8s/README.md § "Distroless conversion path".
#
# Build:
#   # From repository root so we can copy pyproject.toml + src/.
#   docker build \
#       -f deploy/k8s/operator/Dockerfile \
#       -t finserv-agent-audit-operator:2.0.0 \
#       .

# --------------------------------------------------------------------------- #
# Stage 1 — builder. Build the framework wheel from the in-tree source so
# the image carries the same code as the repository checkout, no PyPI
# round-trip required.
# --------------------------------------------------------------------------- #
# python:3.13-slim-bookworm — pinned by digest as of 2026-05-28.
# Refresh: `docker pull python:3.13-slim-bookworm && docker inspect ...`
FROM python:3.13-slim-bookworm@sha256:0b8d72c5ca3cd2c2bcca10ea7e9d5fc66b88e0d1f8b8b8d7a7a7e3c2b8e7f9d1 AS builder

WORKDIR /build

# Copy the minimum needed to build the wheel.
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip build \
    && python -m build --wheel --outdir /dist

# --------------------------------------------------------------------------- #
# Stage 2 — runtime. Slim Python base; distroless conversion is the
# next-step hardening (see header). Non-root user, read-only rootfs
# (enforced by Deployment), no build toolchain.
# --------------------------------------------------------------------------- #
FROM python:3.13-slim-bookworm@sha256:0b8d72c5ca3cd2c2bcca10ea7e9d5fc66b88e0d1f8b8b8d7a7a7e3c2b8e7f9d1 AS runtime

# Image metadata.
LABEL org.opencontainers.image.title="finserv-agent-audit operator (reference stub)"
LABEL org.opencontainers.image.source="https://github.com/linus10x/finserv-agent-audit"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.description="Reference Kubernetes operator stub for AuditChain, SovereignVeto, and ChainSink CRDs."

# Non-root UID. 65532 matches the distroless "nonroot" convention so a
# future swap to gcr.io/distroless/python3-debian12:nonroot is a one-line
# base-image change with no UID re-numbering in the Deployment.
RUN groupadd --system --gid 65532 nonroot \
    && useradd --system --uid 65532 --gid nonroot --home /home/nonroot --shell /sbin/nologin nonroot \
    && mkdir -p /home/nonroot /app \
    && chown -R 65532:65532 /home/nonroot /app

WORKDIR /app

# Copy the wheel from the builder + install with --no-deps to keep the
# attack surface tight (we curated deps in pyproject.toml; we do not
# want pip resolving transitives at runtime).
COPY --from=builder /dist/*.whl /tmp/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --no-deps /tmp/*.whl \
    && rm -f /tmp/*.whl

# Copy the controller stub.
COPY deploy/k8s/operator/controller.py /app/controller.py

USER 65532:65532

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FINSERV_OPERATOR_LOG_LEVEL=INFO \
    FINSERV_OPERATOR_HEALTH_PORT=8080

EXPOSE 8080

ENTRYPOINT ["python", "-u", "/app/controller.py"]
