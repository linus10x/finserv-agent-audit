# PyPI Trusted Publishing Setup

One-time configuration the maintainer performs on PyPI + TestPyPI + GitHub so that `.github/workflows/publish.yml` can publish wheels and sdists without long-lived API tokens, and so each artifact ships with a PEP 740 Sigstore attestation.

This document is operator-facing. It is not loaded at runtime.

---

## What Trusted Publishing is, in two paragraphs

PyPI Trusted Publishing replaces the historical "generate an API token, paste it as a secret, hope it never leaks" credential model with an OpenID Connect (OIDC) trust binding between a PyPI project and a specific GitHub Actions workflow. At publish time, GitHub mints a short-lived OIDC token (typically valid for minutes), the `pypa/gh-action-pypi-publish` action exchanges it with PyPI for an even shorter-lived upload credential, the upload completes, and the credential expires. There is no persistent secret to rotate, exfiltrate, or accidentally commit.

PEP 740 layers a second guarantee on top: each artifact uploaded through Trusted Publishing is signed against the Sigstore public-good transparency log (Rekor). The signing certificate identifies the exact `owner/repo` + workflow file + environment + commit SHA that produced the artifact. Consumers running `pip install` on a recent pip (26.1.1+) can verify these attestations end-to-end. The badge `Sigstore signed` appears next to the version on the PyPI project page when attestations are present.

The combination removes the two highest-residual-risk failure modes of the traditional model: leaked tokens and unsigned tarballs.

---

## Prerequisites

- Maintainer with `Owner` role on the `linus10x/finserv-agent-audit` GitHub repo
- A PyPI account in good standing with 2FA enrolled
- A TestPyPI account in good standing with 2FA enrolled (separate account from PyPI; same email is fine)
- The `publish.yml` workflow in `.github/workflows/` at `main` HEAD

---

## Step 1 — TestPyPI Trusted Publisher (dry-run target)

1. Sign in to https://test.pypi.org/ and open https://test.pypi.org/manage/account/publishing/
2. Under **Add a new pending publisher**, fill in:
   - PyPI Project Name: `finserv-agent-audit`
   - Owner: `linus10x`
   - Repository name: `finserv-agent-audit`
   - Workflow name: `publish.yml`
   - Environment name: `testpypi`
3. Click **Add**. TestPyPI registers a "pending" publisher; the binding upgrades to a real publisher on the first successful upload, which also creates the project.

---

## Step 2 — PyPI Trusted Publisher (production target)

Repeat Step 1 against production PyPI:

1. Sign in to https://pypi.org/ and open https://pypi.org/manage/account/publishing/
2. **Add a new pending publisher** with the same five fields, except set:
   - Environment name: `pypi` (note: lowercase, exact match to the workflow's `environment.name`)
3. Click **Add**.

The first successful publish creates `https://pypi.org/project/finserv-agent-audit/` and pins the binding.

---

## Step 3 — GitHub environments with required reviewers

The workflow declares two environments: `testpypi` and `pypi`. Both need to exist in the repo's environment settings, and the production one should require a reviewer so that a tag push cannot push to PyPI without an explicit human approval.

1. Open https://github.com/linus10x/finserv-agent-audit/settings/environments
2. Click **New environment**, name it `testpypi`, save. No protection rules needed (TestPyPI is dry-run scope).
3. Click **New environment**, name it `pypi`, save. Then:
   - Enable **Required reviewers** and add yourself (and any co-maintainers).
   - Optionally enable **Deployment branches** -> "Selected branches and tags" -> add `v*` to restrict the environment to tag refs.
   - Optionally set a **Wait timer** of 5 minutes for an extra "are you sure" pause.

The environment names in the workflow must match exactly; a typo here is the most common first-publish failure mode.

---

## Step 4 — First publish (dry-run via manual dispatch)

Before tagging anything, exercise the build + TestPyPI path:

1. Go to **Actions** -> **Publish to PyPI** -> **Run workflow** -> branch `main` -> **Run**.
2. The `build` job produces `dist/finserv_agent_audit-1.2.0-py3-none-any.whl` and `dist/finserv_agent_audit-1.2.0.tar.gz`.
3. The `publish-testpypi` job uploads them to TestPyPI. The `publish-pypi` job is skipped because the trigger was `workflow_dispatch`, not a tag push.
4. Verify https://test.pypi.org/project/finserv-agent-audit/1.2.0/ renders, the version shows a `Sigstore signed` badge, and the **Download files** view shows two artifacts plus an attestation bundle.
5. Smoke-install in a scratch venv:

   ```bash
   python -m venv /tmp/scratch && source /tmp/scratch/bin/activate
   pip install -i https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ \
       finserv-agent-audit==1.2.0
   python -c "import finserv_agent_audit; print(finserv_agent_audit.__version__)"
   ```

---

## Step 5 — First production publish (tag push)

1. Confirm `pyproject.toml`, `src/finserv_agent_audit/__init__.py`, and `CITATION.cff` all read `1.2.0` and the `date-released` is set to the real ship date.
2. Tag and push:

   ```bash
   git tag -a v1.2.0 -m "v1.2.0 — OCC 2026-13 response + ecosystem onramps"
   git push origin v1.2.0
   ```

3. The workflow runs `build` -> `publish-testpypi` -> waits for reviewer approval on the `pypi` environment.
4. Approve in the Actions UI.
5. Verify https://pypi.org/project/finserv-agent-audit/1.2.0/ — `Sigstore signed` badge present, both artifacts visible, attestation bundle attached.

---

## Verification of an installed wheel's attestation

On a fresh machine with pip 26.1.1+:

```bash
pip install --require-hashes finserv-agent-audit==1.2.0
pip inspect finserv-agent-audit | grep -i provenance
```

The `provenance` field in `pip inspect` output (or `pip install --verbose` console output) will reference the Sigstore bundle and the `linus10x/finserv-agent-audit` workflow + commit SHA that produced the build.

For a fully manual cryptographic check, download the `.whl` + `.whl.publish.attestation` bundle from the PyPI project page and verify with the `pypi-attestations` CLI (https://github.com/trailofbits/pypi-attestations).

---

## Troubleshooting

### `invalid-publisher: valid token, but no corresponding publisher`

The OIDC token minted by GitHub did not match any registered Trusted Publisher on PyPI. Check, in order:

1. The environment name in the workflow (`environment: name: pypi`) matches the environment name registered on PyPI exactly, including case.
2. The workflow file name on disk is `publish.yml`, matching the value registered on PyPI.
3. The repo owner + repo name match. A repo rename or a fork running the workflow will not satisfy the binding.

### `Permission denied: id-token is not enabled`

The job is missing `permissions: id-token: write`. Both `publish-testpypi` and `publish-pypi` jobs need it. The repo-default `permissions: contents: read` at the workflow top is fine; per-job permissions extend it, they do not replace it.

### `attestations: write` missing

Without `permissions: attestations: write` on the `publish-pypi` job, the upload succeeds but the Sigstore bundle is not written back to PyPI and the `Sigstore signed` badge does not appear. The artifact is still installable; it just lacks the PEP 740 provenance record.

### TestPyPI upload fails with "file already exists"

You re-ran the workflow against the same version. The publish step is configured with `skip-existing: true` for TestPyPI, so this is non-fatal — but if you intend to re-test the same version, bump the version, or delete the TestPyPI release first (TestPyPI allows project-owners to delete; PyPI does not).

### Reviewer-approval prompt never appears

The `pypi` environment is missing the **Required reviewers** rule, or the workflow ran outside a tag push. Manual `workflow_dispatch` runs intentionally short-circuit the `publish-pypi` job via the `if:` guard at the job level.

---

## Rotation + offboarding

Because there are no long-lived secrets, there is nothing to rotate on a schedule. The only operator actions to track:

- If a maintainer leaves the org, remove them from the `pypi` environment's reviewer list.
- If the repo is renamed or transferred, both Trusted Publisher bindings (TestPyPI + PyPI) must be re-registered with the new owner/repo pair.
- If the workflow filename changes from `publish.yml`, update the binding to match.

---

## Reference

- PyPI Trusted Publishing: https://docs.pypi.org/trusted-publishers/
- PEP 740 (Index support for digital attestations): https://peps.python.org/pep-0740/
- `pypa/gh-action-pypi-publish`: https://github.com/pypa/gh-action-pypi-publish
- `pypi-attestations` CLI: https://github.com/trailofbits/pypi-attestations
