"""Tests for the minimal RFC 3161 DER codec.

Byte-vector tests are kept identical to `cre-agent-audit`'s
`tests/test_rfc3161_codec.py` so that any divergence in the hand-rolled DER
codec shows up immediately — both repos depend on the same wire format and
the byte vectors here are the load-bearing parity surface.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from finserv_agent_audit.governance.rfc3161_codec import (
    build_timestamp_request,
    parse_timestamp_response,
)


def test_request_starts_with_der_sequence_tag() -> None:
    digest = hashlib.sha256(b"hello").digest()
    req = build_timestamp_request(digest)
    assert req[0] == 0x30  # SEQUENCE


def test_request_contains_sha256_oid() -> None:
    """OID 2.16.840.1.101.3.4.2.1 (sha256) DER body: 60 86 48 01 65 03 04 02 01"""
    req = build_timestamp_request(hashlib.sha256(b"hello").digest())
    sha256_oid = bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])
    assert sha256_oid in req


def test_request_contains_digest() -> None:
    digest = hashlib.sha256(b"hello").digest()
    req = build_timestamp_request(digest)
    assert digest in req


def test_request_rejects_non_sha256_digest_length() -> None:
    with pytest.raises(ValueError):
        build_timestamp_request(b"short")


def test_parse_synthetic_generalized_time() -> None:
    """Hand-built DER blob with one GeneralizedTime, verifying the parser
    walks the tag and decodes the body. This avoids needing a live TSA."""
    # SEQUENCE wrapping a GeneralizedTime "20260528123456Z"
    body = b"20260528123456Z"
    blob = bytes([0x30, 17, 0x18, 15]) + body  # SEQUENCE(17) > GenTime(15)
    ts = parse_timestamp_response(blob)
    assert ts == datetime(2026, 5, 28, 12, 34, 56, tzinfo=UTC)


def test_parse_generalized_time_with_fractional_seconds() -> None:
    body = b"20260528123456.789Z"
    blob = bytes([0x30, 21, 0x18, 19]) + body
    ts = parse_timestamp_response(blob)
    assert ts.microsecond == 789000
    assert ts.tzinfo == UTC


def test_parse_response_missing_generalized_time_raises() -> None:
    with pytest.raises(ValueError):
        parse_timestamp_response(b"no-gentime-here")


def test_parse_response_indefinite_length_raises() -> None:
    """Construct: SEQUENCE with indefinite length (0x80) — explicitly unsupported."""
    # 0x18 is GenTime; place after a 0x80 length-byte to trigger the check
    # via a SEQUENCE whose length encoder reads 0x80.
    blob = bytes([0x30, 0x80, 0x18, 0x80, 0x00, 0x00])
    with pytest.raises(ValueError):
        parse_timestamp_response(blob)
