# Licensing

`finserv-agent-audit` is dual-licensed under either of:

- **Apache License, Version 2.0** — [LICENSE-APACHE](LICENSE-APACHE) · [apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)
- **MIT license** — [LICENSE-MIT](LICENSE-MIT) · [opensource.org/licenses/MIT](http://opensource.org/licenses/MIT)

at the election of the adopter. Election does not require notice to the maintainer.

`SPDX-License-Identifier: MIT OR Apache-2.0`

## Why dual

The project moved to dual licensing in May 2026 for these reasons:

- **Preserves the v1.0.1 citation graph.** The framework shipped MIT under v1.0.1 (Zenodo DOI `10.5281/zenodo.20434570`); pure replacement with Apache 2.0 would break the citation surface and force re-attribution by every prior adopter.
- **Supplies the express patent grant** that Tier-1 financial-services legal review at major financial institutions routinely requires before authorizing OSS into a regulated supply chain. Apache 2.0 §3 supplies it; MIT does not.
- **Costs nothing at zero external contributors.** The decision is reversible by a future maintainer (a deprecation of one license arm is a semver-minor change); a unilateral re-license away from MIT is not.

## Adopter election

Adopters cite the elected license in their NOTICE, third-party-license inventory, or equivalent. Example forms:

```
finserv-agent-audit (Apache-2.0): https://github.com/linus10x/finserv-agent-audit
```

```
finserv-agent-audit (MIT): https://github.com/linus10x/finserv-agent-audit
```

```
finserv-agent-audit (MIT OR Apache-2.0): https://github.com/linus10x/finserv-agent-audit
```

All three forms satisfy the citation requirement under both licenses.

## Contributing under both licenses

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the project by you, as defined in the Apache License 2.0, shall be dual-licensed as above without any additional terms or conditions.

We require Developer Certificate of Origin (DCO) sign-off on every commit (`Signed-off-by:` line in the commit message; `git commit -s`) per the LF AI & Data Foundation onboarding posture. The DCO is a lightweight inbound-IP hygiene mechanism; it does not require a CLA. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution workflow.

## Trademark

"Autonomy Ladder" and "ALO" are trademarks of Kunjar Bhaduri and are governed separately from the source-code license per Apache 2.0 §6. See [docs/TRADEMARK.md](docs/TRADEMARK.md) for the full trademark posture including the irrevocable nominative-use carve-out for OSS forks, academic citation, and conformance attestation.

## Questions

License questions: open an issue at [github.com/linus10x/finserv-agent-audit/issues](https://github.com/linus10x/finserv-agent-audit/issues) with the `licensing` label.

Patent / SLAs / commercial-redistribution questions: see [SECURITY.md](SECURITY.md) for the maintainer security contact; for commercial-redistribution discussion specifically, contact `licensing@autonomy-ladder.io` (placeholder pending entity formation).
