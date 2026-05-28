"""Tests for the MI Proxy (Module Integrity verifier chain-of-custody).

Test surface: round-trip, tampered binary, missing key, stale attestation,
verifier-hook integration, opaque-claim verify_integrity path. Fail-closed
posture is the load-bearing assertion.

Regulatory anchor (test rationale):
    - SR 11-7 second-line model-validation: the verifier IS a model;
      these tests exercise out-of-band attestation of that model.
    - SOX 404 ITGC: change-management evidence - swap the verifier
      binary and attestation must fail.
"""

from __future__ import annotations

import base64
import secrets
import time
import warnings
from datetime import UTC, datetime, timedelta

import pytest

from finserv_agent_audit.governance.mi_proxy import (
    Attestation,
    IntegrityVerificationError,
    LocalMIProxy,
    MIProxy,
    MIProxyKeyMissingWarning,
    enforce_attestation,
)

# A real module that resolves to a source file on disk - any module in
# the package works; defcon is stable and present in v1.0.
VERIFIER_COMPONENT = "finserv_agent_audit.governance.defcon"


def _fresh_key_b64() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode()


# --------------------------------------------------------------------------- #
# 1. Protocol conformance                                                     #
# --------------------------------------------------------------------------- #


def test_local_mi_proxy_is_a_mi_proxy() -> None:
    """LocalMIProxy conforms to the MIProxy Protocol."""
    proxy: MIProxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    assert hasattr(proxy, "attest")
    assert hasattr(proxy, "verify_attestation")


# --------------------------------------------------------------------------- #
# 2. Round-trip - attest then verify                                          #
# --------------------------------------------------------------------------- #


def test_local_mi_proxy_round_trip_succeeds() -> None:
    """A fresh attestation verifies against the same proxy."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    attestation = proxy.attest(component_id=VERIFIER_COMPONENT)
    assert proxy.verify_attestation(attestation) is True
    assert attestation.component_id == VERIFIER_COMPONENT
    assert attestation.backend_id == "local-hmac"
    assert len(attestation.sha256_hex) == 64
    assert attestation.signature_b64
    # ISO-8601 round-trip
    parsed = datetime.fromisoformat(attestation.timestamp_iso)
    assert parsed.tzinfo is not None


# --------------------------------------------------------------------------- #
# 3. Tampered attestation - any field change fails verify                     #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "field, mutated_value",
    [
        ("component_id", "finserv_agent_audit.governance.different_module"),
        ("sha256_hex", "0" * 64),
        ("timestamp_iso", "2030-01-01T00:00:00+00:00"),
        ("backend_id", "spoofed-backend"),
    ],
)
def test_local_mi_proxy_rejects_tampered_attestation(field: str, mutated_value: str) -> None:
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    attestation = proxy.attest(component_id=VERIFIER_COMPONENT)
    tampered = Attestation(**{**attestation.__dict__, field: mutated_value})
    assert proxy.verify_attestation(tampered) is False


def test_local_mi_proxy_rejects_swapped_signature() -> None:
    """A signature from a different key over the same payload is rejected."""
    proxy_a = LocalMIProxy(signing_key=secrets.token_bytes(32))
    proxy_b = LocalMIProxy(signing_key=secrets.token_bytes(32))
    attestation_b = proxy_b.attest(component_id=VERIFIER_COMPONENT)
    assert proxy_a.verify_attestation(attestation_b) is False


def test_local_mi_proxy_rejects_attestation_of_unknown_component() -> None:
    """attest() raises ImportError for a component that does not resolve."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    with pytest.raises(ImportError):
        proxy.attest(component_id="finserv_agent_audit.governance.does_not_exist")


# --------------------------------------------------------------------------- #
# 4. Missing key - explicit warning + fail-closed                             #
# --------------------------------------------------------------------------- #


def test_local_mi_proxy_warns_when_key_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """No key in env -> MIProxyKeyMissingWarning; attestations sign with zero key."""
    monkeypatch.delenv("FINSERV_AUDIT_MI_PROXY_KEY", raising=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        proxy = LocalMIProxy.from_env()
        proxy.attest(component_id=VERIFIER_COMPONENT)
    key_warnings = [w for w in caught if issubclass(w.category, MIProxyKeyMissingWarning)]
    assert key_warnings, "Expected MIProxyKeyMissingWarning when key absent"


def test_local_mi_proxy_fail_closed_against_real_key_after_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An attestation signed under the zero key does not verify under a real key."""
    monkeypatch.delenv("FINSERV_AUDIT_MI_PROXY_KEY", raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        zero_key_proxy = LocalMIProxy.from_env()
        attestation = zero_key_proxy.attest(component_id=VERIFIER_COMPONENT)
    real_proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    assert real_proxy.verify_attestation(attestation) is False


def test_local_mi_proxy_from_env_with_base64_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_env decodes a base64-encoded key from the env var."""
    key = secrets.token_bytes(32)
    monkeypatch.setenv("FINSERV_AUDIT_MI_PROXY_KEY", base64.b64encode(key).decode())
    proxy = LocalMIProxy.from_env()
    attestation = proxy.attest(component_id=VERIFIER_COMPONENT)
    assert proxy.verify_attestation(attestation) is True


def test_local_mi_proxy_from_env_with_hex_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """from_env decodes a hex-encoded key from the env var."""
    key = secrets.token_bytes(32)
    monkeypatch.setenv("FINSERV_AUDIT_MI_PROXY_KEY", key.hex())
    proxy = LocalMIProxy.from_env()
    attestation = proxy.attest(component_id=VERIFIER_COMPONENT)
    assert proxy.verify_attestation(attestation) is True


def test_local_mi_proxy_rejects_short_key() -> None:
    """Keys shorter than 32 bytes are rejected at construction."""
    with pytest.raises(ValueError):
        LocalMIProxy(signing_key=b"short")


def test_local_mi_proxy_from_env_rejects_malformed_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed env-var value (not base64, not hex, too short) is rejected."""
    monkeypatch.setenv("FINSERV_AUDIT_MI_PROXY_KEY", "not-a-valid-key-shape")
    with pytest.raises(ValueError):
        LocalMIProxy.from_env()


# --------------------------------------------------------------------------- #
# 5. Stale attestation - time-bounded                                         #
# --------------------------------------------------------------------------- #


def test_local_mi_proxy_rejects_stale_attestation() -> None:
    """Attestations older than max_age_seconds fail verify."""
    key = secrets.token_bytes(32)
    proxy = LocalMIProxy(signing_key=key, max_age_seconds=60)

    stale_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    fresh = proxy.attest(component_id=VERIFIER_COMPONENT)
    # Re-sign the stale-timestamped attestation with the same key so that
    # the signature is valid but the timestamp is out of window.
    stale = LocalMIProxy._for_test_resign(
        proxy,
        component_id=fresh.component_id,
        sha256_hex=fresh.sha256_hex,
        timestamp_iso=stale_ts,
        backend_id=fresh.backend_id,
    )
    assert proxy.verify_attestation(stale) is False


def test_local_mi_proxy_accepts_fresh_attestation_within_window() -> None:
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32), max_age_seconds=3600)
    attestation = proxy.attest(component_id=VERIFIER_COMPONENT)
    assert proxy.verify_attestation(attestation) is True


def test_local_mi_proxy_rejects_naive_timestamp() -> None:
    """An attestation with a timezone-naive timestamp is rejected."""
    key = secrets.token_bytes(32)
    proxy = LocalMIProxy(signing_key=key)
    fresh = proxy.attest(component_id=VERIFIER_COMPONENT)
    naive = LocalMIProxy._for_test_resign(
        proxy,
        component_id=fresh.component_id,
        sha256_hex=fresh.sha256_hex,
        timestamp_iso="2026-05-28T12:00:00",  # no tzinfo
        backend_id=fresh.backend_id,
    )
    assert proxy.verify_attestation(naive) is False


def test_local_mi_proxy_rejects_malformed_timestamp() -> None:
    """A signature-valid attestation with an unparseable timestamp is rejected."""
    key = secrets.token_bytes(32)
    proxy = LocalMIProxy(signing_key=key)
    fresh = proxy.attest(component_id=VERIFIER_COMPONENT)
    bad = LocalMIProxy._for_test_resign(
        proxy,
        component_id=fresh.component_id,
        sha256_hex=fresh.sha256_hex,
        timestamp_iso="not-an-iso-timestamp",
        backend_id=fresh.backend_id,
    )
    assert proxy.verify_attestation(bad) is False


# --------------------------------------------------------------------------- #
# 6. Verifier-hook integration - fail-closed when proxy attests false         #
# --------------------------------------------------------------------------- #


def test_enforce_attestation_passes_when_attestation_valid() -> None:
    """enforce_attestation returns normally when attestation succeeds."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    enforce_attestation(proxy, VERIFIER_COMPONENT)  # must not raise


def test_enforce_attestation_raises_integrity_error_on_failure() -> None:
    """enforce_attestation raises IntegrityVerificationError when MIProxy fails."""

    class AlwaysFailMIProxy:
        def attest(self, component_id: str) -> Attestation:
            return Attestation(
                component_id=component_id,
                sha256_hex="f" * 64,
                timestamp_iso=datetime.now(UTC).isoformat(),
                signature_b64="invalid",
                backend_id="test-fail",
            )

        def verify_attestation(self, attestation: Attestation) -> bool:
            return False

    with pytest.raises(IntegrityVerificationError):
        enforce_attestation(AlwaysFailMIProxy(), VERIFIER_COMPONENT)


def test_enforce_attestation_raises_on_unknown_component() -> None:
    """An unknown component bubbles ImportError out of attest()."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    with pytest.raises(ImportError):
        enforce_attestation(proxy, "finserv_agent_audit.governance.does_not_exist")


# --------------------------------------------------------------------------- #
# 7. Opaque claim - verify_integrity higher-level surface                     #
# --------------------------------------------------------------------------- #


def test_verify_integrity_round_trip_succeeds() -> None:
    """attest_claim -> verify_integrity round-trips a deployer-supplied claim."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    claim = b'{"slsa_provenance": "v1.0", "build_id": "abc123"}'
    attestation = proxy.attest_claim(claim)
    assert proxy.verify_integrity(claim, attestation) is True


def test_verify_integrity_rejects_tampered_claim() -> None:
    """A different claim under the same attestation fails verify."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    attestation = proxy.attest_claim(b"original-claim")
    assert proxy.verify_integrity(b"tampered-claim", attestation) is False


def test_verify_integrity_rejects_swapped_key() -> None:
    """An attestation produced under a different key fails verify."""
    proxy_a = LocalMIProxy(signing_key=secrets.token_bytes(32))
    proxy_b = LocalMIProxy(signing_key=secrets.token_bytes(32))
    claim = b"some-claim"
    attestation_b = proxy_b.attest_claim(claim)
    assert proxy_a.verify_integrity(claim, attestation_b) is False


def test_verify_integrity_rejects_malformed_attestation() -> None:
    """Garbage attestation bytes return False, never raise."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    assert proxy.verify_integrity(b"claim", b"not-a-valid-token") is False
    assert proxy.verify_integrity(b"claim", b"") is False


# --------------------------------------------------------------------------- #
# 8. Performance budget - local backend must stay cheap                       #
# --------------------------------------------------------------------------- #


def test_attest_latency_local_backend() -> None:
    """Local backend target: ~5ms per call (50ms generous CI ceiling)."""
    proxy = LocalMIProxy(signing_key=secrets.token_bytes(32))
    start = time.perf_counter()
    for _ in range(10):
        attestation = proxy.attest(component_id=VERIFIER_COMPONENT)
        proxy.verify_attestation(attestation)
    elapsed_ms_per_call = ((time.perf_counter() - start) * 1000) / 10
    assert elapsed_ms_per_call < 50, f"Attest+verify took {elapsed_ms_per_call:.2f}ms/call"


# --------------------------------------------------------------------------- #
# 9. Bonus: helper exposed for callers                                        #
# --------------------------------------------------------------------------- #


def test_fresh_key_helper_produces_decodable_key() -> None:
    """_fresh_key_b64 produces a 32+ byte base64 string LocalMIProxy.from_env accepts."""
    raw = _fresh_key_b64()
    decoded = base64.b64decode(raw)
    assert len(decoded) >= 32
