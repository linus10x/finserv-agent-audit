"""Minimal DER ASN.1 codec for RFC 3161 TimeStampReq / TimeStampResp.

Trusted timestamping is load-bearing for financial-services audit posture:

- **SEC 17a-4(f)** requires broker-dealer electronic records to be preserved
  in a non-rewriteable, non-erasable format with a verifiable time anchor.
- **eIDAS Regulation (EU 910/2014) Article 42** designates qualified
  electronic timestamps (RFC 3161 the wire format underneath) as having
  legal presumption of accuracy and integrity across the EU.
- **Federal Reserve SR 11-7 (2011) — Guidance on Model Risk Management**
  requires model-validation evidence be retained with trusted time anchoring
  so the validator can demonstrate when a given model decision was made.

This module implements only the DER subset RFC 3161 actually exercises:
OID, INTEGER, OCTET STRING, NULL, BOOLEAN, SEQUENCE, GeneralizedTime.

Stdlib-only — the zero-runtime-dependencies posture of finserv-agent-audit
forbids pulling in `cryptography` or `pyasn1` for the build/parse path.
Full signature verification (TSA cert chain, signing-cert revocation) is
intentionally out of scope for this codec; the opaque TSR token is preserved
verbatim alongside the parsed `genTime` so a downstream verifier with the
heavier crypto stack can re-validate at any time.

RFC 3161 references:
- Section 2.4.1 — TimeStampReq
- Section 2.4.2 — TimeStampResp
- Section 2.4.2 — TSTInfo.genTime (GeneralizedTime, YYYYMMDDHHMMSS[.fff]Z)
"""

from __future__ import annotations

from datetime import UTC, datetime

# OID 2.16.840.1.101.3.4.2.1 — id-sha256 (DER body bytes)
_SHA256_OID = bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])

# DER tags
_TAG_BOOLEAN = 0x01
_TAG_INTEGER = 0x02
_TAG_OCTET_STRING = 0x04
_TAG_NULL = 0x05
_TAG_OID = 0x06
_TAG_GENERALIZED_TIME = 0x18
_TAG_SEQUENCE = 0x30


def _encode_length(n: int) -> bytes:
    if n < 128:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(value)) + value


def build_timestamp_request(payload_digest: bytes) -> bytes:
    """Build a SHA-256 TimeStampReq DER blob for `payload_digest` (32 bytes)."""
    if len(payload_digest) != 32:
        raise ValueError("payload_digest must be 32 bytes (SHA-256)")
    # AlgorithmIdentifier { sha256 OID, NULL params }
    algo_id = _tlv(
        _TAG_SEQUENCE,
        _tlv(_TAG_OID, _SHA256_OID) + _tlv(_TAG_NULL, b""),
    )
    # MessageImprint { hashAlgorithm, hashedMessage }
    message_imprint = _tlv(
        _TAG_SEQUENCE,
        algo_id + _tlv(_TAG_OCTET_STRING, payload_digest),
    )
    # TimeStampReq { version=1, messageImprint, certReq=TRUE }
    version = _tlv(_TAG_INTEGER, bytes([1]))
    cert_req = _tlv(_TAG_BOOLEAN, bytes([0xFF]))
    return _tlv(_TAG_SEQUENCE, version + message_imprint + cert_req)


def parse_timestamp_response(tsr_bytes: bytes) -> datetime:
    """Extract GeneralizedTime from a TimeStampResp DER blob.

    The TSR wraps PKCSContentInfo wrapping SignedData wrapping eContent
    (an OCTET STRING) wrapping TSTInfo (a SEQUENCE) — TSTInfo.genTime is
    a GeneralizedTime in YYYYMMDDHHMMSS[.fff]Z form.

    We scan for the first GeneralizedTime tag inside the response. This is
    sufficient because TSTInfo.genTime is the only GeneralizedTime in the
    structure; finding the tag is unambiguous for well-formed TSRs.
    """
    i = 0
    while i < len(tsr_bytes):
        if tsr_bytes[i] == _TAG_GENERALIZED_TIME:
            length, header_len = _decode_length_at(tsr_bytes, i + 1)
            value = tsr_bytes[i + 1 + header_len : i + 1 + header_len + length]
            return _parse_generalized_time(value)
        i += 1
    raise ValueError("no GeneralizedTime found in TSR")


def _decode_length_at(buf: bytes, offset: int) -> tuple[int, int]:
    """Return (length, header_byte_count_after_offset)."""
    first = buf[offset]
    if first < 0x80:
        return first, 1
    num_bytes = first & 0x7F
    if num_bytes == 0:
        raise ValueError("indefinite-length DER not supported")
    length = int.from_bytes(buf[offset + 1 : offset + 1 + num_bytes], "big")
    return length, 1 + num_bytes


def _parse_generalized_time(value: bytes) -> datetime:
    """Parse YYYYMMDDHHMMSS[.fff]Z into UTC datetime."""
    s = value.decode("ascii")
    if not s.endswith("Z"):
        raise ValueError("GeneralizedTime must end with Z (UTC)")
    s = s[:-1]
    if "." in s:
        base, frac = s.split(".", 1)
        micro = int(frac.ljust(6, "0")[:6])
    else:
        base, micro = s, 0
    if len(base) != 14:
        raise ValueError(f"unexpected GeneralizedTime body {value!r}")
    return datetime(
        year=int(base[0:4]),
        month=int(base[4:6]),
        day=int(base[6:8]),
        hour=int(base[8:10]),
        minute=int(base[10:12]),
        second=int(base[12:14]),
        microsecond=micro,
        tzinfo=UTC,
    )
