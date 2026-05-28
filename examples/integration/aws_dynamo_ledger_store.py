"""DynamoDB-backed ``LedgerStore`` with conditional writes (reference).

What this integration does
--------------------------
Implements ``LedgerStore`` against an AWS DynamoDB table. Each ``append``
is a ``PutItem`` with ``ConditionExpression=attribute_not_exists(sequence)``
on the ``(chain_id, sequence)`` key. Two writers racing on sequence N
will see exactly one succeed; the loser raises and must re-read head.
DynamoDB single-item conditional-write strong-consistency delivers the
linearizability the chain requires without an external lock.

Schema (table ``audit_chain``): PK chain_id (S) | SK sequence (N) plus
event_id, event_type, autonomy_level, agent_id, timestamp, payload_json,
actor_id?, prev_hash, event_hash, schema_version (all S).

Talks to AWS DynamoDB via an injected ``boto3.client("dynamodb")``.
``boto3`` is NOT a runtime dep — the import is guarded; the demo uses
an in-memory stub when boto3 is absent.

Regulatory framework benefits
-----------------------------
- **SR 11-7** — firm-wide model inventory needs horizontal scale;
  DynamoDB on-demand handles N parallel writers without provisioning.
- **GLBA Safeguards Rule** — pair with KMS CMK + VPC endpoints to keep
  customer NPI inside the customer's AWS account.
- **SEC Rule 17a-4** — pair with PITR + S3 Object Lock exports for the
  6-year non-rewriteable retention pass; this table is the searchable
  primary, S3 Object Lock is the WORM copy of record.
- **NYDFS Part 500.06** — linearizable append meets "designed to
  reconstruct."

REFERENCE integration. Not on the package surface; no runtime dep added.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from finserv_agent_audit.governance.ledger_store import GENESIS_PREV_HASH
from finserv_agent_audit.schemas.audit_event import (
    AuditEvent,
    AuditEventType,
    AutonomyLevel,
)

try:
    import boto3  # noqa: F401
    from botocore.exceptions import ClientError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

    class ClientError(Exception):  # type: ignore[no-redef]
        """Fallback when botocore is absent; never raised in stub mode."""


class DynamoDBLedgerStore:
    """``LedgerStore`` Protocol implementation backed by DynamoDB.

    Caller injects a ``boto3.client("dynamodb")`` so the store does not
    own credentials or region resolution. Append uses a conditional
    ``PutItem`` to prevent split-brain on (chain_id, sequence).
    """

    def __init__(
        self,
        table_name: str,
        client: Any,
        *,
        chain_id: str = "default",
    ) -> None:
        self._table_name = table_name
        self._client = client
        self._chain_id = chain_id

    def append(self, event: AuditEvent) -> None:
        next_seq = self.head_sequence() + 1
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=self._event_to_item(event, next_seq),
                ConditionExpression="attribute_not_exists(#seq)",
                ExpressionAttributeNames={"#seq": "sequence"},
            )
        except ClientError as err:
            code = getattr(err, "response", {}).get("Error", {}).get("Code", "")
            if code == "ConditionalCheckFailedException":
                raise RuntimeError(
                    f"split-brain at seq {next_seq} on chain {self._chain_id!r}"
                ) from err
            raise

    def __iter__(self) -> Iterator[AuditEvent]:
        kw: dict[str, Any] = {
            "TableName": self._table_name,
            "KeyConditionExpression": "chain_id = :cid",
            "ExpressionAttributeValues": {":cid": {"S": self._chain_id}},
            "ConsistentRead": True,
        }
        while True:
            resp = self._client.query(**kw)
            yield from (self._item_to_event(it) for it in resp.get("Items", []))
            if "LastEvaluatedKey" not in resp:
                return
            kw["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    def __len__(self) -> int:
        return self.head_sequence() + 1

    def get(self, sequence: int) -> AuditEvent:
        resp = self._client.get_item(
            TableName=self._table_name,
            Key={"chain_id": {"S": self._chain_id}, "sequence": {"N": str(sequence)}},
            ConsistentRead=True,
        )
        item = resp.get("Item")
        if item is None:
            raise IndexError(f"sequence {sequence} not found on {self._chain_id!r}")
        return self._item_to_event(item)

    def head_sequence(self) -> int:
        resp = self._client.query(
            TableName=self._table_name,
            KeyConditionExpression="chain_id = :cid",
            ExpressionAttributeValues={":cid": {"S": self._chain_id}},
            ScanIndexForward=False,
            Limit=1,
            ConsistentRead=True,
            ProjectionExpression="#seq",
            ExpressionAttributeNames={"#seq": "sequence"},
        )
        items = resp.get("Items") or []
        return int(items[0]["sequence"]["N"]) if items else -1

    def head_event_hash(self) -> str:
        head = self.head_sequence()
        if head < 0:
            return str(GENESIS_PREV_HASH)
        return str(self.get(head).event_hash)

    def _event_to_item(self, event: AuditEvent, sequence: int) -> dict[str, Any]:
        item: dict[str, Any] = {
            "chain_id": {"S": self._chain_id},
            "sequence": {"N": str(sequence)},
            "event_id": {"S": event.event_id},
            "event_type": {"S": event.event_type.value},
            "autonomy_level": {"S": event.autonomy_level.value},
            "agent_id": {"S": event.agent_id},
            "timestamp": {"S": event.timestamp},
            "payload_json": {"S": json.dumps(event.payload, sort_keys=True)},
            "prev_hash": {"S": event.prev_hash},
            "event_hash": {"S": event.event_hash},
            "schema_version": {"S": event.schema_version},
        }
        if event.actor_id is not None:
            item["actor_id"] = {"S": event.actor_id}
        return item

    @staticmethod
    def _item_to_event(item: dict[str, Any]) -> AuditEvent:
        actor_attr = item.get("actor_id")
        event = AuditEvent(
            event_type=AuditEventType(item["event_type"]["S"]),
            autonomy_level=AutonomyLevel(item["autonomy_level"]["S"]),
            agent_id=item["agent_id"]["S"],
            payload=json.loads(item["payload_json"]["S"]),
            prev_hash=item["prev_hash"]["S"],
            event_id=item["event_id"]["S"],
            timestamp=item["timestamp"]["S"],
            actor_id=actor_attr["S"] if actor_attr is not None else None,
            schema_version=item["schema_version"]["S"],
        )
        event.event_hash = item["event_hash"]["S"]
        return event


# Demo: in-memory stub of the DynamoDB client shape (no boto3, no AWS)
class _StubDynamoClient:
    """In-memory stub of the boto3 DynamoDB client surface used by
    ``DynamoDBLedgerStore``. Honors the conditional-write so the
    split-brain detector runs end-to-end without AWS."""

    class _Err(Exception):
        def __init__(self, code: str) -> None:
            super().__init__(code)
            self.response = {"Error": {"Code": code}}

    def __init__(self) -> None:
        self._store: dict[tuple[str, int], dict[str, Any]] = {}

    def put_item(self, **kw: Any) -> dict[str, Any]:
        item = kw["Item"]
        key = (item["chain_id"]["S"], int(item["sequence"]["N"]))
        if kw.get("ConditionExpression") == "attribute_not_exists(#seq)" and key in self._store:
            raise self._Err("ConditionalCheckFailedException")
        self._store[key] = item
        return {}

    def get_item(self, **kw: Any) -> dict[str, Any]:
        k = (kw["Key"]["chain_id"]["S"], int(kw["Key"]["sequence"]["N"]))
        item = self._store.get(k)
        return {"Item": item} if item is not None else {}

    def query(self, **kw: Any) -> dict[str, Any]:
        cid = kw["ExpressionAttributeValues"][":cid"]["S"]
        items = [v for (k_cid, _seq), v in self._store.items() if k_cid == cid]
        items.sort(
            key=lambda it: int(it["sequence"]["N"]), reverse=not kw.get("ScanIndexForward", True)
        )
        limit = kw.get("Limit")
        return {"Items": items[:limit] if limit is not None else items}


def _run_demo() -> None:
    src = "boto3 available; stub anyway" if HAS_BOTO3 else "boto3 NOT installed; using stub"
    print(f"DynamoDBLedgerStore demo: {src}")
    print("(live AWS demo: inject boto3.client('dynamodb') + a real table)")
    client = _StubDynamoClient()
    store = DynamoDBLedgerStore("audit_chain", client, chain_id="demo")
    prev = GENESIS_PREV_HASH
    for i in range(5):
        ev = AuditEvent(
            event_type=AuditEventType.DECISION_MADE,
            autonomy_level=AutonomyLevel.A2,
            agent_id="demo:dynamo",
            payload={"step": i, "action": "noop"},
            prev_hash=prev,
        )
        store.append(ev)
        prev = ev.event_hash
    print(f"appended            : {len(store)} events (iter yields {len(list(store))})")
    print(f"head_sequence       : {store.head_sequence()}")
    print(f"head_event_hash     : {store.head_event_hash()}")
    try:
        client.put_item(
            TableName="audit_chain",
            Item=store._event_to_item(store.get(0), 0),  # noqa: SLF001
            ConditionExpression="attribute_not_exists(#seq)",
            ExpressionAttributeNames={"#seq": "sequence"},
        )
        print("split-brain check   : FAILED to detect duplicate (bug)")
    except _StubDynamoClient._Err as err:
        print(f"split-brain check   : detected duplicate -> {err.args[0]}")


if __name__ == "__main__":
    _run_demo()
