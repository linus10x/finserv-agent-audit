"""Reference integration examples — OPTIONAL.

These modules show how the four ``finserv_agent_audit`` Protocol seams
(``LedgerStore``, ``TimestampSource``, ``WitnessRegister``, ``MIProxy``)
plug into real production infrastructure. They are NOT imported by the
package surface and they do NOT add runtime dependencies to the wheel.

Modules:
    splunk_audit_sink         - LedgerStore -> Splunk HEC (SOX 404 ITGC)
    datadog_audit_sink        - LedgerStore -> Datadog Logs API
    sigstore_rekor_witness    - WitnessRegister -> Sigstore Rekor (live)
    aws_dynamo_ledger_store   - LedgerStore -> DynamoDB conditional writes

Each module ships a runnable ``__main__`` demo that either uses a stdlib
mock (Splunk, Datadog) or gracefully skips when network / optional deps
are unavailable (Rekor, DynamoDB).
"""

__all__: list[str] = []
