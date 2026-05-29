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
OID, INTEGER, OCTET STRING, NULL, BOOLEAN, SEQUENCE, GeneralizedTime, and
the context-tag [0] EXPLICIT wrappers CMS uses for the SignedData content
and the TSTInfo eContent OCTET STRING.

Stdlib-only — the zero-runtime-dependencies posture of finserv-agent-audit
forbids pulling in `cryptography` or `pyasn1` for the build/parse path.
Full signature verification (TSA cert chain, signing-cert revocation) is
intentionally out of scope for this codec; the opaque TSR token is preserved
verbatim alongside the parsed `genTime` so a downstream verifier with the
heavier crypto stack can re-validate at any time.

CR-6 hardening (v2.0):

1. `_decode_length_at` is bounds-checked end-to-end. Length encodings
   exceeding 4 bytes (32-bit lengths) and fields claiming more than
   ``_MAX_FIELD_BYTES`` are rejected — closes CWE-190 / CWE-400 (the
   `0x84 FF FF FF FF` 4-gigabyte length-of-claim DoS vector).
2. `parse_timestamp_response` performs a STRUCTURAL ASN.1 walk through the
   ContentInfo / SignedData / encapContentInfo / TSTInfo nesting. The
   legacy byte-scan returned the first ``0x18`` byte it saw, which could
   land inside a CertificateSerialNumber INTEGER body and let an
   adversarial TSA return attacker-chosen timestamps. Closes
   CWE-20 / CWE-1284.

RFC 3161 references:
- Section 2.4.1 — TimeStampReq
- Section 2.4.2 — TimeStampResp
- Section 2.4.2 — TSTInfo.genTime (GeneralizedTime, YYYYMMDDHHMMSS[.fff]Z)
"""

from __future__ import annotations

from datetime import UTC, datetime

# OID 2.16.840.1.101.3.4.2.1 — id-sha256 (DER body bytes)
_SHA256_OID = bytes([0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01])

# OID 1.2.840.113549.1.7.2 — id-signedData (CMS SignedData)
_ID_SIGNED_DATA_OID = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x07, 0x02])

# OID 1.2.840.113549.1.9.16.1.4 — id-ct-TSTInfo (RFC 3161 TSTInfo content type)
_ID_CT_TST_INFO_OID = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x09, 0x10, 0x01, 0x04])

# DER tags
_TAG_BOOLEAN = 0x01
_TAG_INTEGER = 0x02
_TAG_OCTET_STRING = 0x04
_TAG_NULL = 0x05
_TAG_OID = 0x06
_TAG_ENUMERATED = 0x0A
_TAG_UTF8_STRING = 0x0C
_TAG_PRINTABLE_STRING = 0x13
_TAG_GENERALIZED_TIME = 0x18
_TAG_SEQUENCE = 0x30
_TAG_SET = 0x31

# Context-specific [0] EXPLICIT (constructed) — used by CMS ContentInfo
# wrapper and encapContentInfo's eContent OCTET STRING.
_TAG_CONTEXT_0_CONSTRUCTED = 0xA0

# Hardening caps. RFC 3161 TSRs from real TSAs are well under 100 KB
# (full chain + sigs typically 5-20 KB). Anything larger is either a
# malformed response or a DoS payload. The 4-byte length cap rejects
# the canonical `0x84 FF FF FF FF` 4 GB length-claim attack.
_MAX_LENGTH_BYTES = 4
_MAX_FIELD_BYTES = 100_000


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


def _decode_length_at(buf: bytes, offset: int) -> tuple[int, int]:
    """Decode the DER length octet(s) at ``offset``.

    Returns ``(length, header_byte_count_after_offset)``. Bounds-checked
    against every CR-6 attack vector:

    - ``offset`` must be inside ``buf``.
    - Indefinite-length encoding (``0x80``) is rejected — illegal in DER.
    - Long-form encodings claiming more than ``_MAX_LENGTH_BYTES`` length
      bytes are rejected (so ``0x85`` and beyond never decode).
    - The declared length must not exceed ``_MAX_FIELD_BYTES``.
    - The declared length plus the header must not run past ``buf``.

    Only ``ValueError`` is raised on malformed input; this is the contract
    the fuzz harness pins.
    """
    if offset >= len(buf):
        raise ValueError(f"DER length decode at offset {offset} exceeds buffer of {len(buf)}")
    first = buf[offset]
    if first & 0x80 == 0:
        # short form: length is the byte value itself
        length = first
        if offset + 1 + length > len(buf):
            raise ValueError(
                f"DER short-form length {length} would read past buffer at offset {offset}"
            )
        return (length, 1)
    num_bytes = first & 0x7F
    if num_bytes == 0:
        raise ValueError("DER indefinite-length encoding is illegal in DER (only BER)")
    if num_bytes > _MAX_LENGTH_BYTES:
        raise ValueError(
            f"DER length encoding claims {num_bytes} length bytes (max {_MAX_LENGTH_BYTES})"
        )
    if offset + 1 + num_bytes > len(buf):
        raise ValueError("DER length encoding header would read past buffer")
    length = int.from_bytes(buf[offset + 1 : offset + 1 + num_bytes], "big")
    if length > _MAX_FIELD_BYTES:
        raise ValueError(f"DER field length {length} exceeds max {_MAX_FIELD_BYTES}")
    if offset + 1 + num_bytes + length > len(buf):
        raise ValueError(f"DER length {length} would read past buffer at offset {offset}")
    return (length, 1 + num_bytes)


def _read_tlv(buf: bytes, offset: int) -> tuple[int, bytes, int]:
    """Read one TLV at ``offset``. Returns ``(tag, value, next_offset)``."""
    if offset >= len(buf):
        raise ValueError(f"TLV read at offset {offset} exceeds buffer of {len(buf)}")
    tag = buf[offset]
    length, header_len = _decode_length_at(buf, offset + 1)
    value_start = offset + 1 + header_len
    value_end = value_start + length
    return (tag, buf[value_start:value_end], value_end)


def _expect_tag(actual: int, expected: int, context: str) -> None:
    if actual != expected:
        raise ValueError(
            f"DER structural walk: expected tag 0x{expected:02X} ({context}), got 0x{actual:02X}"
        )


def parse_timestamp_response(tsr_bytes: bytes) -> datetime:
    """Parse RFC 3161 TimeStampResp and extract ``TSTInfo.genTime``.

    Implements a STRUCTURAL ASN.1 walk through the nested wrappers:

    ::

        TimeStampResp ::= SEQUENCE {
          status           PKIStatusInfo,
          timeStampToken   TimeStampToken OPTIONAL }

        TimeStampToken ::= ContentInfo                       -- CMS SignedData

        ContentInfo ::= SEQUENCE {
          contentType   ContentType,                         -- id-signedData
          content       [0] EXPLICIT ANY DEFINED BY contentType }

        SignedData ::= SEQUENCE {
          version           CMSVersion,
          digestAlgorithms  SET OF DigestAlgorithmIdentifier,
          encapContentInfo  EncapsulatedContentInfo,
          ... }

        EncapsulatedContentInfo ::= SEQUENCE {
          eContentType  ContentType,                         -- id-ct-TSTInfo
          eContent      [0] EXPLICIT OCTET STRING OPTIONAL } -- holds TSTInfo

        TSTInfo ::= SEQUENCE {
          version           INTEGER,
          policy            TSAPolicyId,
          messageImprint    MessageImprint,
          serialNumber      INTEGER,
          genTime           GeneralizedTime,
          ... }

    The walk validates that ``contentType == id-signedData`` and
    ``eContentType == id-ct-TSTInfo`` before descending. The returned
    ``genTime`` is the FIFTH element of TSTInfo — the legacy byte-scan
    that returned the first ``0x18`` byte could land inside the
    CertificateSerialNumber INTEGER body and hand an adversarial TSA a
    free choice of timestamp (CWE-20 / CWE-1284).

    Only ``ValueError`` is raised on malformed input.
    """
    # --- TimeStampResp ---
    tag, resp_body, _ = _read_tlv(tsr_bytes, 0)
    _expect_tag(tag, _TAG_SEQUENCE, "TimeStampResp")

    # PKIStatusInfo — skip; we only care about the token. PKIStatusInfo is
    # itself a SEQUENCE, so the next TLV inside resp_body is it.
    status_tag, _status_body, after_status = _read_tlv(resp_body, 0)
    _expect_tag(status_tag, _TAG_SEQUENCE, "PKIStatusInfo")

    if after_status >= len(resp_body):
        raise ValueError("TimeStampResp has no timeStampToken (status-only response)")

    # --- ContentInfo (the TimeStampToken) ---
    ct_tag, ct_body, _ = _read_tlv(resp_body, after_status)
    _expect_tag(ct_tag, _TAG_SEQUENCE, "ContentInfo")

    # ContentInfo.contentType — MUST be id-signedData
    oid_tag, oid_body, after_oid = _read_tlv(ct_body, 0)
    _expect_tag(oid_tag, _TAG_OID, "ContentInfo.contentType")
    if oid_body != _ID_SIGNED_DATA_OID:
        raise ValueError("ContentInfo.contentType is not id-signedData (1.2.840.113549.1.7.2)")

    # ContentInfo.content — [0] EXPLICIT wrapping the SignedData SEQUENCE
    ctx_tag, ctx_body, _ = _read_tlv(ct_body, after_oid)
    _expect_tag(ctx_tag, _TAG_CONTEXT_0_CONSTRUCTED, "ContentInfo.content [0]")

    sd_tag, sd_body, _ = _read_tlv(ctx_body, 0)
    _expect_tag(sd_tag, _TAG_SEQUENCE, "SignedData")

    # --- SignedData fields ---
    # CMSVersion INTEGER
    ver_tag, _ver_body, after_ver = _read_tlv(sd_body, 0)
    _expect_tag(ver_tag, _TAG_INTEGER, "SignedData.version")

    # digestAlgorithms SET
    da_tag, _da_body, after_da = _read_tlv(sd_body, after_ver)
    _expect_tag(da_tag, _TAG_SET, "SignedData.digestAlgorithms")

    # encapContentInfo SEQUENCE
    eci_tag, eci_body, _ = _read_tlv(sd_body, after_da)
    _expect_tag(eci_tag, _TAG_SEQUENCE, "SignedData.encapContentInfo")

    # encapContentInfo.eContentType — MUST be id-ct-TSTInfo
    ect_tag, ect_body, after_ect = _read_tlv(eci_body, 0)
    _expect_tag(ect_tag, _TAG_OID, "encapContentInfo.eContentType")
    if ect_body != _ID_CT_TST_INFO_OID:
        raise ValueError(
            "encapContentInfo.eContentType is not id-ct-TSTInfo (1.2.840.113549.1.9.16.1.4)"
        )

    # encapContentInfo.eContent — [0] EXPLICIT wrapping an OCTET STRING
    if after_ect >= len(eci_body):
        raise ValueError("encapContentInfo has no eContent (TSTInfo missing)")

    e_ctx_tag, e_ctx_body, _ = _read_tlv(eci_body, after_ect)
    _expect_tag(e_ctx_tag, _TAG_CONTEXT_0_CONSTRUCTED, "encapContentInfo.eContent [0]")

    oct_tag, oct_body, _ = _read_tlv(e_ctx_body, 0)
    _expect_tag(oct_tag, _TAG_OCTET_STRING, "eContent OCTET STRING")

    # --- TSTInfo ---
    tst_tag, tst_body, _ = _read_tlv(oct_body, 0)
    _expect_tag(tst_tag, _TAG_SEQUENCE, "TSTInfo")

    # TSTInfo.version INTEGER
    t_ver_tag, _t_ver_body, after_t_ver = _read_tlv(tst_body, 0)
    _expect_tag(t_ver_tag, _TAG_INTEGER, "TSTInfo.version")

    # TSTInfo.policy OID
    pol_tag, _pol_body, after_pol = _read_tlv(tst_body, after_t_ver)
    _expect_tag(pol_tag, _TAG_OID, "TSTInfo.policy")

    # TSTInfo.messageImprint SEQUENCE
    mi_tag, _mi_body, after_mi = _read_tlv(tst_body, after_pol)
    _expect_tag(mi_tag, _TAG_SEQUENCE, "TSTInfo.messageImprint")

    # TSTInfo.serialNumber INTEGER — the field whose body can contain 0x18
    # and trips the legacy byte-scanner.
    sn_tag, _sn_body, after_sn = _read_tlv(tst_body, after_mi)
    _expect_tag(sn_tag, _TAG_INTEGER, "TSTInfo.serialNumber")

    # TSTInfo.genTime GeneralizedTime — the field we actually care about.
    gt_tag, gt_body, _ = _read_tlv(tst_body, after_sn)
    _expect_tag(gt_tag, _TAG_GENERALIZED_TIME, "TSTInfo.genTime")

    return _parse_generalized_time(gt_body)


def _parse_generalized_time(value: bytes) -> datetime:
    """Parse YYYYMMDDHHMMSS[.fff]Z into UTC datetime."""
    try:
        s = value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"GeneralizedTime body is not ASCII: {value!r}") from exc
    if not s.endswith("Z"):
        raise ValueError("GeneralizedTime must end with Z (UTC)")
    s = s[:-1]
    if "." in s:
        base, frac = s.split(".", 1)
        if not frac or not frac.isdigit():
            raise ValueError(f"GeneralizedTime fractional part invalid: {value!r}")
        micro = int(frac.ljust(6, "0")[:6])
    else:
        base, micro = s, 0
    if len(base) != 14 or not base.isdigit():
        raise ValueError(f"unexpected GeneralizedTime body {value!r}")
    try:
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
    except ValueError:
        # Out-of-range component (month=13, day=32, etc.) — keep the ValueError
        # contract but ensure the message mentions the source bytes.
        raise ValueError(f"GeneralizedTime body out of range: {value!r}") from None
