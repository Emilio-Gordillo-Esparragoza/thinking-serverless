import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
from shared.utils.logger import get_logger, log_struct

logger = get_logger(__name__)


def _parse_sqs_event(event: Dict[str, Any]) -> list[Dict[str, Any]]:
    records = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            detail = json.loads(body.get("detail", "{}"))
            records.append(detail)
        except (KeyError, json.JSONDecodeError) as e:
            log_struct(logger, logger.level, "Failed to parse SQS record", error=str(e))
    return records


def _build_ledger_entries(
    transaction: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    tx_id = transaction.get("transactionId", "unknown")
    account_id = transaction.get("accountId", "unknown")
    amount = transaction.get("amount", 0)
    tx_type = transaction.get("type", "unknown")
    now = datetime.now(timezone.utc).isoformat()

    debit = {
        "entryId": f"{tx_id}-debit",
        "accountId": account_id,
        "amount": amount,
        "direction": "debit",
        "description": f"{tx_type} debit",
        "bookedAt": now,
    }
    credit = {
        "entryId": f"{tx_id}-credit",
        "accountId": account_id,
        "amount": amount,
        "direction": "credit",
        "description": f"{tx_type} credit",
        "bookedAt": now,
    }
    return debit, credit


def lambda_handler(event: Dict[str, Any], context: Any) -> None:
    transactions = _parse_sqs_event(event)
    if not transactions:
        log_struct(logger, logger.level, "No valid transactions to process")
        return

    for tx in transactions:
        debit, credit = _build_ledger_entries(tx)
        log_struct(
            logger,
            logger.level,
            "Ledger entry created",
            transactionId=tx.get("transactionId"),
            debitEntryId=debit["entryId"],
            creditEntryId=credit["entryId"],
            amount=tx.get("amount"),
            currency=tx.get("currency", "USD"),
        )
