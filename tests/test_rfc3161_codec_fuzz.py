"""Hypothesis fuzz harness for the RFC 3161 DER codec.

Closes CR-6 (DER codec hardening). Two CWE classes are in scope:

- **CWE-190 / CWE-400 (memory-DoS / integer-overflow):** an adversarial TSA
  can emit a DER length byte `0x84 FF FF FF FF` claiming a 4GB length; the
  codec must reject the encoding instead of allocating against the claim.
- **CWE-20 / CWE-1284 (improper input validation):** an adversarial TSA can
  emit a TimeStampResp whose first `0x18` byte falls inside a
  CertificateSerialNumber INTEGER body — the legacy byte-scanner returns
  the attacker-chosen value instead of `TSTInfo.genTime`.

Property: for any bytes input, the parser MUST either return a `datetime`
or raise `ValueError`. Any other exception type (IndexError, MemoryError,
OverflowError, UnicodeDecodeError) is a finding.
"""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")

from datetime import datetime  # noqa: E402

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from finserv_agent_audit.governance.rfc3161_codec import (  # noqa: E402
    _decode_length_at,
    parse_timestamp_response,
)


@given(st.binary(max_size=4096))
@settings(max_examples=2000, suppress_health_check=[HealthCheck.too_slow])
def test_parse_timestamp_response_never_crashes_on_arbitrary_bytes(
    data: bytes,
) -> None:
    """Adversarial TSR input must EITHER return datetime OR raise ValueError.

    Never crash, hang, or return wrong-time silently.
    """
    try:
        result = parse_timestamp_response(data)
        # if we got a result, it must be a datetime
        assert isinstance(result, datetime)
    except ValueError:
        # ValueError is the documented error path — expected
        pass
    except Exception as e:
        pytest.fail(f"unexpected exception type {type(e).__name__}: {e}")


@given(st.binary(max_size=100), st.integers(min_value=0, max_value=99))
@settings(max_examples=1000)
def test_decode_length_at_never_crashes(data: bytes, offset: int) -> None:
    """_decode_length_at must EITHER succeed OR raise ValueError.

    Never IndexError, MemoryError, OverflowError.
    """
    if offset >= len(data):
        return  # skip — out-of-range offset is caller's responsibility
    try:
        length, header_len = _decode_length_at(data, offset)
        assert length >= 0
        assert header_len > 0
    except ValueError:
        # ValueError is the documented error path — expected; any OTHER
        # exception type fails the property below.
        pass
    except Exception as e:
        pytest.fail(f"unexpected exception type {type(e).__name__}: {e}")


def test_decode_length_at_rejects_5byte_length_encoding() -> None:
    """0x85 (5 length bytes) is rejected — caps at 4-byte (32-bit) lengths."""
    # 0x85 0x01 0x02 0x03 0x04 0x05 claims a 5-byte length encoding
    buf = bytes([0x85, 0x01, 0x02, 0x03, 0x04, 0x05]) + b"\x00" * 1000
    with pytest.raises(ValueError, match="length bytes"):
        _decode_length_at(buf, 0)


def test_decode_length_at_rejects_oversize_field() -> None:
    """A 4-byte length claiming >100KB is rejected as a DoS payload."""
    # 0x84 0x00 0x10 0x00 0x00 = length of 1,048,576 (1 MB)
    buf = bytes([0x84, 0x00, 0x10, 0x00, 0x00]) + b"\x00" * 200
    with pytest.raises(ValueError, match="exceeds max"):
        _decode_length_at(buf, 0)


def test_decode_length_at_rejects_4byte_4gb_claim() -> None:
    """The CR-6 canonical attack: 0x84 FF FF FF FF claims a 4GB field."""
    buf = bytes([0x84, 0xFF, 0xFF, 0xFF, 0xFF]) + b"\x00" * 100
    with pytest.raises(ValueError, match="exceeds max"):
        _decode_length_at(buf, 0)


def test_decode_length_at_rejects_length_past_buffer() -> None:
    """A declared length that runs past the buffer is rejected."""
    # short-form length of 100 (< 0x80, so still short-form) with only
    # 9 bytes of payload following — declared length runs past buffer.
    buf = bytes([100]) + b"\x00" * 9
    with pytest.raises(ValueError, match="past buffer"):
        _decode_length_at(buf, 0)


def test_decode_length_at_rejects_indefinite_length() -> None:
    """0x80 (indefinite length) is illegal in DER; only BER allows it."""
    buf = bytes([0x80, 0x00, 0x00])
    with pytest.raises(ValueError, match="indefinite"):
        _decode_length_at(buf, 0)


def test_decode_length_at_truncated_length_bytes() -> None:
    """A long-form length byte without enough following length bytes is rejected."""
    # claims 4 length bytes follow, but only 2 are present
    buf = bytes([0x84, 0x00, 0x01])
    with pytest.raises(ValueError, match="past buffer"):
        _decode_length_at(buf, 0)


def test_parse_rejects_gentime_inside_certificate_serial() -> None:
    """CR-6 part B: adversarial TSR with a 0x18 byte inside an INTEGER body.

    The legacy byte-scan parser returned the INTEGER bytes as a timestamp.
    The structural walk MUST reject this — there is no valid
    ContentInfo/SignedData/TSTInfo wrapper, so it raises ValueError.
    """
    # Outer SEQUENCE wrapping an INTEGER whose body happens to start with 0x18.
    # Legacy byte-scanner would have hit 0x18 (the INTEGER body byte) and
    # tried to decode "20260528123456Z"-shaped bytes from the serial.
    fake_gentime_in_serial = (
        bytes(
            [
                0x30,
                0x13,  # SEQUENCE (19 bytes)
                0x02,
                0x11,  # INTEGER (17 bytes) — body below
                0x18,
                0x0F,  # body starts with 0x18, 0x0F …
            ]
        )
        + b"20260528123456Z"
    )  # … and a fake gen-time string
    with pytest.raises(ValueError):
        parse_timestamp_response(fake_gentime_in_serial)
