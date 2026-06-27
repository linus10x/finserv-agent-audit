"""CR-1 — ``AuditChainTamperError`` MUST be the same class across import paths.

Two prior locations defined the exception independently:

  * ``finserv_agent_audit.governance.audit_chain.AuditChainTamperError``
  * ``finserv_agent_audit.agents.base.AuditChainTamperError``

Adopter code catching one would not catch the other — every ``except``
in the adopter's process would silently miss the half of the call graph
that raised the sibling class. The fix consolidates both names onto the
governance canonical class and re-exports it from the agents package.

This test asserts class identity, not just structural equivalence: if a
future refactor re-introduces a parallel definition, ``A is B`` flips
to ``False`` and the regression is caught at CI time rather than at
adopter post-mortem time.
"""

from __future__ import annotations


def test_audit_chain_tamper_error_is_one_class_across_packages() -> None:
    """Both import paths MUST resolve to the same class object."""
    from finserv_agent_audit.agents import AuditChainTamperError as A
    from finserv_agent_audit.governance import AuditChainTamperError as B

    assert A is B


def test_audit_chain_tamper_error_canonical_module() -> None:
    """The canonical home is ``governance.audit_chain``; both alias to it."""
    from finserv_agent_audit.agents import AuditChainTamperError as via_agents  # noqa: N813
    from finserv_agent_audit.governance.audit_chain import (
        AuditChainTamperError as canonical,  # noqa: N813
    )

    assert via_agents is canonical
    assert canonical.__module__ == "finserv_agent_audit.governance.audit_chain"


def test_governance_error_caught_via_agents_path() -> None:
    """An exception raised through the governance path MUST be caught
    by an ``except`` written against the agents path."""
    import pytest

    from finserv_agent_audit.agents import AuditChainTamperError as ViaAgents
    from finserv_agent_audit.governance import AuditChainTamperError as ViaGovernance

    with pytest.raises(ViaAgents):
        raise ViaGovernance("simulated")


def test_agents_error_caught_via_governance_path() -> None:
    """An exception raised through the agents path MUST be caught
    by an ``except`` written against the governance path."""
    import pytest

    from finserv_agent_audit.agents import AuditChainTamperError as ViaAgents
    from finserv_agent_audit.governance import AuditChainTamperError as ViaGovernance

    with pytest.raises(ViaGovernance):
        raise ViaAgents("simulated")


def test_agents_base_also_resolves_to_canonical_class() -> None:
    """``agents.base`` re-export MUST be the canonical class, not a sibling."""
    from finserv_agent_audit.agents.base import AuditChainTamperError as via_base  # noqa: N813
    from finserv_agent_audit.governance.audit_chain import (
        AuditChainTamperError as canonical,  # noqa: N813
    )

    assert via_base is canonical
