"""Subject-ID hashing for GLBA / GDPR-safe audit-chain payloads.

Raw customer_id / consumer_id / subject_id values MUST NOT be written
directly to audit-chain payloads. The hash-chain is tamper-evident
within-trust-boundary; PII written into the chain cannot be erased
(GDPR Art. 17 collision) and cannot be encrypted at rest at the chain
layer (GLBA Safeguards Rule).

HashedSubjectId is a deployer-keyed HMAC-SHA256 of the subject ID
using a peppered key the deployer holds OUTSIDE the audit chain.
Operators can re-key the pepper to invalidate all chain-recorded
hashed-IDs (effective erasure) without breaking chain integrity.

Regulatory anchors:
    - GLBA Safeguards Rule, 16 C.F.R. Part 314 — NPI encrypted at rest
    - GDPR Art. 17 — right to erasure (the "right to be forgotten")
    - CCPA / CPRA — consumer data deletion request
    - ADR-0033 (subject-id hashing seam)

> Reference pattern, not legal advice. Engage privacy counsel for
> deletion-workflow design and key-management requirements specific
> to your jurisdiction.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

_PEPPER_ENV_VAR = "FINSERV_AUDIT_SUBJECT_ID_PEPPER"
_MIN_PEPPER_BYTES = 32


@dataclass(frozen=True)
class HashedSubjectId:
    """A keyed HMAC of a raw subject identifier.

    Fields:
        hash_b64: base64-encoded HMAC-SHA256 digest (44 chars w/ padding).
        pepper_version: deployer-set version tag; rotate to invalidate
            historical hashes (effective erasure on a tamper-evident hash-chain).
        algorithm: name of the keyed-hash algorithm (default HMAC-SHA256).
    """

    hash_b64: str
    pepper_version: str
    algorithm: str = "HMAC-SHA256"


@runtime_checkable
class SubjectIdHasher(Protocol):
    """Protocol seam for hashing subject IDs before they enter the chain."""

    def hash_subject(self, raw_subject_id: str) -> HashedSubjectId: ...


class HMACSubjectIdHasher:
    """Reference HMAC-SHA256 hasher with a deployer-held pepper.

    The pepper is loaded from the ``FINSERV_AUDIT_SUBJECT_ID_PEPPER``
    environment variable when no explicit ``pepper`` is passed. The
    pepper must be at least ``MIN_PEPPER_BYTES`` (32) bytes. Rotate
    the pepper (and bump ``pepper_version``) to invalidate every
    previously-recorded HashedSubjectId — the effective-erasure
    pathway when a customer invokes GDPR Art. 17.
    """

    def __init__(
        self,
        pepper: bytes | None = None,
        pepper_version: str = "v1",
    ) -> None:
        if pepper is None:
            pepper_env = os.environ.get(_PEPPER_ENV_VAR)
            if not pepper_env:
                raise ValueError(
                    f"{_PEPPER_ENV_VAR} env var not set; cannot hash subject IDs safely"
                )
            pepper = pepper_env.encode("utf-8")
        if len(pepper) < _MIN_PEPPER_BYTES:
            raise ValueError(f"pepper must be >={_MIN_PEPPER_BYTES} bytes, got {len(pepper)}")
        self._pepper = bytes(pepper)
        self._pepper_version = pepper_version

    def hash_subject(self, raw_subject_id: str) -> HashedSubjectId:
        mac = hmac.new(
            self._pepper,
            raw_subject_id.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return HashedSubjectId(
            hash_b64=base64.b64encode(mac).decode("ascii"),
            pepper_version=self._pepper_version,
        )


__all__ = [
    "HMACSubjectIdHasher",
    "HashedSubjectId",
    "SubjectIdHasher",
]
