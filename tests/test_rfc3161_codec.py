"""Tests for the minimal RFC 3161 DER codec.

Byte-vector tests are kept identical to `cre-agent-audit`'s
`tests/test_rfc3161_codec.py` so that any divergence in the hand-rolled DER
codec shows up immediately — both repos depend on the same wire format and
the byte vectors here are the load-bearing parity surface.

CR-6 hardening (v2.0): the hand-built TSR fixtures here are now full
``ContentInfo > SignedData > encapContentInfo > TSTInfo`` structures rather
than bare ``SEQUENCE > GenTime`` blobs. The structural-walk parser
(introduced to close the CWE-20 byte-scan vulnerability) requires the real
wrapper to walk to the canonical ``TSTInfo.genTime`` position.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from finserv_agent_audit.governance.rfc3161_codec import (
    build_timestamp_request,
    parse_timestamp_response,
)

# --- DER construction helpers (mirrors the codec's private helpers) -----------

_TAG_INTEGER = 0x02
_TAG_OCTET_STRING = 0x04
_TAG_OID = 0x06
_TAG_GENERALIZED_TIME = 0x18
_TAG_SEQUENCE = 0x30
_TAG_SET = 0x31
_TAG_CONTEXT_0 = 0xA0

_ID_SIGNED_DATA_OID = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02])
_ID_CT_TST_INFO_OID = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x09, 0x10, 0x01, 0x04])
# id-sha256 OID body
_SHA256_OID = bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])


def _encode_length(n: int) -> bytes:
    if n < 128:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(value)) + value


def _build_tstinfo(gen_time_body: bytes, serial_body: bytes = b"\x01") -> bytes:
    """Build a minimal TSTInfo SEQUENCE with the given GeneralizedTime body."""
    version = _tlv(_TAG_INTEGER, bytes([1]))
    # Use the TSA-policy OID slot with a placeholder OID (id-sha256 is reused
    # here purely as a syntactically-valid OID — the parser does not validate it).
    policy = _tlv(_TAG_OID, _SHA256_OID)
    # MessageImprint { AlgorithmIdentifier{sha256, NULL}, OCTET STRING(32) }
    algo_id = _tlv(_TAG_SEQUENCE, _tlv(_TAG_OID, _SHA256_OID) + _tlv(0x05, b""))
    digest = b"\x00" * 32
    msg_imprint = _tlv(_TAG_SEQUENCE, algo_id + _tlv(_TAG_OCTET_STRING, digest))
    serial = _tlv(_TAG_INTEGER, serial_body)
    gen_time = _tlv(_TAG_GENERALIZED_TIME, gen_time_body)
    return _tlv(
        _TAG_SEQUENCE,
        version + policy + msg_imprint + serial + gen_time,
    )


def _build_tsr(gen_time_body: bytes, serial_body: bytes = b"\x01") -> bytes:
    """Build a minimal spec-compliant TimeStampResp wrapping the given genTime."""
    tst_info = _build_tstinfo(gen_time_body, serial_body=serial_body)
    octet_string = _tlv(_TAG_OCTET_STRING, tst_info)
    e_content = _tlv(_TAG_CONTEXT_0, octet_string)
    encap = _tlv(
        _TAG_SEQUENCE,
        _tlv(_TAG_OID, _ID_CT_TST_INFO_OID) + e_content,
    )
    # SignedData { version=3, digestAlgorithms={}, encapContentInfo }
    version = _tlv(_TAG_INTEGER, bytes([3]))
    digest_algorithms = _tlv(_TAG_SET, b"")
    signed_data = _tlv(_TAG_SEQUENCE, version + digest_algorithms + encap)
    # ContentInfo { OID = id-signedData, [0] SignedData }
    content_info = _tlv(
        _TAG_SEQUENCE,
        _tlv(_TAG_OID, _ID_SIGNED_DATA_OID) + _tlv(_TAG_CONTEXT_0, signed_data),
    )
    # PKIStatusInfo { status=granted INTEGER }
    pki_status = _tlv(_TAG_SEQUENCE, _tlv(_TAG_INTEGER, bytes([0])))
    return _tlv(_TAG_SEQUENCE, pki_status + content_info)


# --- request-side tests -------------------------------------------------------


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


# --- response-side tests ------------------------------------------------------


def test_parse_synthetic_generalized_time() -> None:
    """Build a real spec-compliant TimeStampResp wrapping a GeneralizedTime
    and verify the structural-walk parser extracts TSTInfo.genTime."""
    tsr = _build_tsr(b"20260528123456Z")
    ts = parse_timestamp_response(tsr)
    assert ts == datetime(2026, 5, 28, 12, 34, 56, tzinfo=UTC)


def test_parse_generalized_time_with_fractional_seconds() -> None:
    tsr = _build_tsr(b"20260528123456.789Z")
    ts = parse_timestamp_response(tsr)
    assert ts.microsecond == 789000
    assert ts.tzinfo == UTC


def test_parse_response_missing_generalized_time_raises() -> None:
    """Random bytes with no DER structure must be rejected with ValueError."""
    with pytest.raises(ValueError):
        parse_timestamp_response(b"no-gentime-here")


def test_parse_response_indefinite_length_raises() -> None:
    """A SEQUENCE with indefinite length (0x80) — illegal in DER."""
    blob = bytes([0x30, 0x80, 0x18, 0x80, 0x00, 0x00])
    with pytest.raises(ValueError):
        parse_timestamp_response(blob)


def test_parse_resists_gentime_byte_in_serial_number() -> None:
    """CR-6 part B regression: a serial number whose body starts with 0x18
    must NOT be mistaken for the genTime. The structural walk lands on the
    real genTime, which here is a different date than what the byte-scan
    parser would have returned from the serial body."""
    # Serial number whose body begins with 0x18 0x0F (looks like a GenTime
    # tag-and-length sequence to the legacy byte-scanner) followed by
    # plausible GenTime bytes pointing at year 2099.
    poisoned_serial = bytes([0x18, 0x0F]) + b"20990101000000Z"
    tsr = _build_tsr(b"20260528123456Z", serial_body=poisoned_serial)
    ts = parse_timestamp_response(tsr)
    # Structural walk MUST return the real genTime (2026), not the poison (2099).
    assert ts == datetime(2026, 5, 28, 12, 34, 56, tzinfo=UTC)


def test_parse_rejects_wrong_content_oid() -> None:
    """ContentInfo.contentType must be id-signedData — anything else rejected."""
    # Replace the id-signedData OID with id-sha256 to corrupt the wrapper.
    tsr = _build_tsr(b"20260528123456Z")
    # Locate the id-signedData OID bytes and swap them for a different OID
    # of identical length so the surrounding lengths stay valid. Both OIDs
    # have a 9-byte DER body — swap directly.
    poisoned = tsr.replace(_ID_SIGNED_DATA_OID, _SHA256_OID, 1)
    with pytest.raises(ValueError, match="id-signedData"):
        parse_timestamp_response(poisoned)
