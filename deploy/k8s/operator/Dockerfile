# Reference Dockerfile for the finserv-agent-audit Kubernetes operator stub.
#
# This image is REFERENCE-ONLY. Production deployers should rebuild on top of
# operator-sdk or kopf rather than the stdlib stub controller. The image
# exists so the deploy/k8s/README.md walkthrough can be followed end-to-end
# in a kind / minikube / dev cluster without bespoke build steps.
FROM python:3.12-slim AS base

# Image metadata.
LABEL org.opencontainers.image.title="finserv-agent-audit operator (reference stub)"
LABEL org.opencontainers.image.source="https://github.com/linus10x/finserv-agent-audit"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.description="Reference Kubernetes operator stub for AuditChain, SovereignVeto, and ChainSink CRDs."

# Non-root user for the stub controller.
RUN groupadd --system finserv && useradd --system --gid finserv --home /home/finserv finserv \
    && mkdir -p /home/finserv && chown -R finserv:finserv /home/finserv

WORKDIR /opt/finserv-operator

# Install the framework wheel. The stub controller imports
# finserv_agent_audit.governance.* directly when reconciling CRDs.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "finserv-agent-audit==1.3.0"

# Copy the stub controller.
COPY controller.py /opt/finserv-operator/controller.py

USER finserv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FINSERV_OPERATOR_LOG_LEVEL=INFO

ENTRYPOINT ["python", "-u", "/opt/finserv-operator/controller.py"]
