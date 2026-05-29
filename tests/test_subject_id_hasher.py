"""Tests for HMACSubjectIdHasher (ADR-0033 / CR-8).

The hasher is the GLBA / GDPR-safe wrapper around customer / consumer /
subject identifiers before they enter the hash-chain payload. The chain
is the integrity artifact, so PII written into it creates a paradox
between the tamper-evident hash-chain (modification detection but not
prevention) and the GDPR Art. 17 right to erasure; the same PII is
also unencrypted at rest under the GLBA Safeguards Rule. The HMAC
pepper lives outside the chain and is re-keyable by deployers —
re-keying invalidates all chain-recorded hashed subject IDs (effective
erasure) without breaking chain integrity.
"""

from __future__ import annotations

import base64
import secrets

import pytest

from finserv_agent_audit.governance.subject_id import (
    HashedSubjectId,
    HMACSubjectIdHasher,
    SubjectIdHasher,
)

# --------------------------------------------------------------------------- #
# 1. Protocol conformance                                                     #
# --------------------------------------------------------------------------- #


def test_hmac_subject_id_hasher_satisfies_protocol() -> None:
    """HMACSubjectIdHasher is structurally a SubjectIdHasher."""
    hasher: SubjectIdHasher = HMACSubjectIdHasher(pepper=secrets.token_bytes(32))
    assert hasattr(hasher, "hash_subject")


# --------------------------------------------------------------------------- #
# 2. Round-trip determinism                                                   #
# --------------------------------------------------------------------------- #


def test_same_pepper_same_input_yields_same_hash() -> None:
    pepper = secrets.token_bytes(32)
    hasher = HMACSubjectIdHasher(pepper=pepper)
    a = hasher.hash_subject("customer-001")
    b = hasher.hash_subject("customer-001")
    assert a.hash_b64 == b.hash_b64
    assert a.algorithm == "HMAC-SHA256"


def test_different_inputs_yield_different_hashes() -> None:
    pepper = secrets.token_bytes(32)
    hasher = HMACSubjectIdHasher(pepper=pepper)
    a = hasher.hash_subject("customer-001")
    b = hasher.hash_subject("customer-002")
    assert a.hash_b64 != b.hash_b64


def test_different_peppers_yield_different_hashes_for_same_input() -> None:
    h1 = HMACSubjectIdHasher(pepper=secrets.token_bytes(32))
    h2 = HMACSubjectIdHasher(pepper=secrets.token_bytes(32))
    a = h1.hash_subject("customer-001")
    b = h2.hash_subject("customer-001")
    assert a.hash_b64 != b.hash_b64


# --------------------------------------------------------------------------- #
# 3. Hash never carries cleartext                                             #
# --------------------------------------------------------------------------- #


def test_hashed_subject_id_does_not_contain_cleartext() -> None:
    """The hashed value must not embed the raw subject id."""
    pepper = secrets.token_bytes(32)
    hasher = HMACSubjectIdHasher(pepper=pepper)
    raw = "consumer-1234567890-very-distinctive"
    hashed = hasher.hash_subject(raw)
    assert raw not in hashed.hash_b64
    # Decoded bytes also must not contain the raw text.
    decoded = base64.b64decode(hashed.hash_b64)
    assert raw.encode("utf-8") not in decoded


def test_hashed_subject_id_is_fixed_length() -> None:
    """HMAC-SHA256 -> 32 bytes -> 44 base64 chars (with padding)."""
    pepper = secrets.token_bytes(32)
    hasher = HMACSubjectIdHasher(pepper=pepper)
    short = hasher.hash_subject("a")
    long_ = hasher.hash_subject("x" * 10_000)
    assert len(short.hash_b64) == len(long_.hash_b64) == 44


# --------------------------------------------------------------------------- #
# 4. Pepper hygiene                                                           #
# --------------------------------------------------------------------------- #


def test_short_pepper_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="pepper must be"):
        HMACSubjectIdHasher(pepper=b"short")


def test_pepper_version_propagates_to_hashed_id() -> None:
    pepper = secrets.token_bytes(32)
    hasher = HMACSubjectIdHasher(pepper=pepper, pepper_version="v7")
    hashed = hasher.hash_subject("customer-001")
    assert hashed.pepper_version == "v7"


# --------------------------------------------------------------------------- #
# 5. Env-var loading + missing-pepper fail-closed                             #
# --------------------------------------------------------------------------- #


def test_env_var_loading_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    pepper_str = "x" * 48
    monkeypatch.setenv("FINSERV_AUDIT_SUBJECT_ID_PEPPER", pepper_str)
    hasher = HMACSubjectIdHasher()
    a = hasher.hash_subject("customer-001")
    assert a.hash_b64
    assert a.pepper_version == "v1"


def test_missing_env_var_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FINSERV_AUDIT_SUBJECT_ID_PEPPER", raising=False)
    with pytest.raises(ValueError, match="FINSERV_AUDIT_SUBJECT_ID_PEPPER"):
        HMACSubjectIdHasher()


# --------------------------------------------------------------------------- #
# 6. HashedSubjectId immutability                                             #
# --------------------------------------------------------------------------- #


def test_hashed_subject_id_is_frozen() -> None:
    hashed = HashedSubjectId(hash_b64="abc", pepper_version="v1")
    with pytest.raises((AttributeError, Exception)):
        hashed.hash_b64 = "xyz"  # type: ignore[misc]
