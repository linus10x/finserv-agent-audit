# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report vulnerabilities by emailing the maintainer directly via LinkedIn:
https://linkedin.com/in/kunjarbhaduri

You will receive an acknowledgment within 48 hours and a resolution timeline within 7 days.

## Security Design Principles

This repository contains reference implementations — not production-ready code.
Before deploying any pattern in a regulated environment:

1. **Review all threshold values** — the values in `defcon_state_machine.py` are illustrative examples. Calibrate to your system's risk tolerance before deploying.
2. **Implement access controls** — ensure only authorized agents and operators can call `manual_override()` and `SovereignVeto.clear()`. Implement proper access controls, including read-only IAM permission boundaries for all agent roles. Refer to the pattern documentation in this repository as content is published.
3. **Encrypt audit logs at rest** — the audit chain provides tamper detection but not confidentiality. Encrypt `*.jsonl` files appropriate to your data classification.
4. **Test the hash chain verifier** — run `AuditChain.verify()` on a schedule and alert on failures.
5. **Never log secrets in payloads** — the `AuditEvent.payload` field accepts arbitrary dicts. Ensure your application layer strips credentials, PII, and strategy logic before logging.
