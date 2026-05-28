"""Drift-detection parity test: FAILURE-MODES.md  <-->  codebase.

The matrix in ``FAILURE-MODES.md`` is treated as a contract. Every
``(F) module.path.callable`` reference in the matrix must resolve to a
real, callable attribute in this codebase. Every
``NOT YET IMPLEMENTED · tracking: ADR-XXXX`` marker must be backed by a
real ADR file under ``docs/adr/`` whose body acknowledges the deferral.

If a callable named in the matrix disappears, this test fails — the doc
becomes false the moment the code drifts. If a tracking-ADR is renamed
or removed without updating the matrix, this test fails — the deferral
loses its receipt.

The test is deliberately small and stdlib-only. The matrix is parsed
with a regex over the markdown table; the ADR check is a directory
scan with a small substring whitelist. No optional dependencies.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
FAILURE_MODES_PATH: Path = REPO_ROOT / "FAILURE-MODES.md"
ADR_DIR: Path = REPO_ROOT / "docs" / "adr"

# Regex pulls out every fully-qualified callable reference. Matches the
# rendered matrix form ``(F) finserv_agent_audit.governance.x.Y.method``.
# The callable path is at least two dotted segments so ``F`` plus a bare
# token cannot match.
_CALLABLE_RE = re.compile(r"\(F\)\s+([a-zA-Z_][\w\.]+(?:\.[a-zA-Z_]\w*){1,})")

# Regex for the explicit deferral marker. Captures the ADR identifier so
# the test can verify the named ADR exists. The matrix uses identifiers
# like ``ADR-0014-A1`` (sub-amendment style); the regex permits the
# letter-digit suffix.
_TRACKING_RE = re.compile(
    r"NOT YET IMPLEMENTED\s*[\xb7\-]\s*tracking:\s*(ADR-\d{4}(?:-[A-Za-z0-9]+)?)"
)

# Substring signals the test accepts as evidence that an ADR
# acknowledges a deferral. Any one of these in the ADR body is enough.
_DEFERRAL_SIGNALS: tuple[str, ...] = (
    "NOT YET IMPLEMENTED",
    "deferred",
    "Deferred",
    "stub",
    "Stub",
    "not yet implemented",
    "v1.2",
)

# A few ADR-id forms in the matrix are sub-amendments (ADR-0014-A1,
# ADR-0014-A2) whose primary ADR file is ``0014-...md``. Map the
# sub-amendment to the canonical filename prefix the directory scan
# should look for.
_SUB_AMENDMENT_TO_PRIMARY: dict[str, str] = {
    "ADR-0014-A1": "0014-",
    "ADR-0014-A2": "0014-",
}


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def matrix_text() -> str:
    assert FAILURE_MODES_PATH.exists(), f"missing {FAILURE_MODES_PATH}"
    return FAILURE_MODES_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def adr_files() -> dict[str, Path]:
    assert ADR_DIR.exists(), f"missing {ADR_DIR}"
    out: dict[str, Path] = {}
    for path in sorted(ADR_DIR.glob("*.md")):
        out[path.name] = path
    return out


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _resolve_dotted(path: str) -> tuple[bool, str]:
    """Resolve a dotted path to (module, attr) and probe it.

    Returns (ok, error-message). On success the second element is empty.
    The function tries progressively-shorter module prefixes so it can
    handle both ``pkg.mod.func`` (module + attr) and
    ``pkg.mod.Class.method`` (module + class + attr).
    """
    parts = path.split(".")
    for split in range(len(parts) - 1, 0, -1):
        module_path = ".".join(parts[:split])
        attr_chain = parts[split:]
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            continue
        obj: object = module
        try:
            for piece in attr_chain:
                obj = getattr(obj, piece)
        except AttributeError as exc:
            return False, (
                f"{path!r}: imported {module_path!r} but attribute walk "
                f"{attr_chain!r} failed at {exc}"
            )
        if not callable(obj):
            return False, f"{path!r}: resolved to non-callable {type(obj).__name__}"
        return True, ""
    return False, f"{path!r}: no importable module prefix found"


def _adr_filename_for(adr_id: str) -> str:
    """Return the four-digit prefix used in the ADR filename.

    ``ADR-0014`` -> ``0014-``; ``ADR-0014-A1`` -> ``0014-`` (the
    sub-amendment is tracked inside the primary ADR's body, not as a
    separate file).
    """
    if adr_id in _SUB_AMENDMENT_TO_PRIMARY:
        return _SUB_AMENDMENT_TO_PRIMARY[adr_id]
    # ``ADR-0019`` -> ``0019-``.
    _, _, digits = adr_id.partition("-")
    return f"{digits}-"


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


class TestMatrixDocumentExists:
    """Sanity envelope. If these fail, every other test in this file is moot."""

    def test_failure_modes_file_present(self) -> None:
        assert FAILURE_MODES_PATH.exists()
        assert FAILURE_MODES_PATH.stat().st_size > 0

    def test_adr_directory_present(self, adr_files: dict[str, Path]) -> None:
        assert len(adr_files) >= 19  # v1.1 ships 19 governance ADRs

    def test_matrix_parses_at_least_one_callable(self, matrix_text: str) -> None:
        matches = _CALLABLE_RE.findall(matrix_text)
        # The matrix ships with at least the six shipped-detection rows.
        # If the regex matches zero, the matrix has drifted from the
        # documented format and downstream parity tests would silently
        # pass.
        assert len(matches) >= 6, (
            f"failure-modes matrix parse degenerated: only {len(matches)} (F) "
            f"references found; matrix format may have changed."
        )


class TestCallableParity:
    """Every ``(F) module.path.callable`` in the matrix resolves to a real callable."""

    def test_all_matrix_callables_resolve(self, matrix_text: str) -> None:
        callable_refs = _CALLABLE_RE.findall(matrix_text)
        # De-dupe — the matrix mentions the same callable in multiple
        # rows (e.g. AuditChain.verify_strict appears in rows 2 and 3).
        unique_refs = sorted(set(callable_refs))

        failures: list[str] = []
        for ref in unique_refs:
            ok, msg = _resolve_dotted(ref)
            if not ok:
                failures.append(msg)

        assert not failures, (
            "FAILURE-MODES.md references callables that do not exist in the "
            "codebase (drift between doc and code):\n  - " + "\n  - ".join(failures)
        )


class TestDeferralTrackingParity:
    """Every ``NOT YET IMPLEMENTED · tracking: ADR-XXXX`` marker has a real ADR."""

    def test_all_tracking_markers_have_adr_files(
        self, matrix_text: str, adr_files: dict[str, Path]
    ) -> None:
        tracking_refs = _TRACKING_RE.findall(matrix_text)
        # Same de-dupe rationale as callables.
        unique_refs = sorted(set(tracking_refs))

        # The matrix's deferred-row tracking column is part of its
        # contract; if the regex matches zero, either the matrix has no
        # deferrals or the format drifted.
        assert len(unique_refs) >= 1, (
            "No NOT-YET-IMPLEMENTED tracking markers found; matrix format may have drifted."
        )

        failures: list[str] = []
        for adr_id in unique_refs:
            prefix = _adr_filename_for(adr_id)
            hits = [name for name in adr_files if name.startswith(prefix)]
            if not hits:
                failures.append(
                    f"{adr_id!r}: no ADR file under {ADR_DIR} matches prefix {prefix!r}"
                )

        assert not failures, (
            "FAILURE-MODES.md cites tracking ADRs that do not exist on disk:\n  - "
            + "\n  - ".join(failures)
        )

    def test_tracking_adrs_acknowledge_deferral(
        self, matrix_text: str, adr_files: dict[str, Path]
    ) -> None:
        tracking_refs = sorted(set(_TRACKING_RE.findall(matrix_text)))
        failures: list[str] = []
        for adr_id in tracking_refs:
            prefix = _adr_filename_for(adr_id)
            hits = [name for name in adr_files if name.startswith(prefix)]
            if not hits:
                continue  # earlier test already reports this
            adr_path = adr_files[hits[0]]
            body = adr_path.read_text(encoding="utf-8")
            if not any(signal in body for signal in _DEFERRAL_SIGNALS):
                failures.append(
                    f"{adr_id!r} ({adr_path.name}): no deferral signal "
                    f"({_DEFERRAL_SIGNALS}) found in the ADR body"
                )
        assert not failures, (
            "Tracking ADRs do not acknowledge the deferral they cover:\n  - "
            + "\n  - ".join(failures)
        )
