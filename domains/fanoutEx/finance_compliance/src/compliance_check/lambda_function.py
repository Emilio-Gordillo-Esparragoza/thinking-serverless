import json
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
from shared.utils.logger import get_logger, log_struct

logger = get_logger(__name__)

AML_THRESHOLD_CENTS = int(os.getenv("AML_THRESHOLD_CENTS", "1000000"))


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


def _run_aml_check(transaction: Dict[str, Any]) -> Dict[str, Any]:
    amount = transaction.get("amount", 0)
    flagged = amount > AML_THRESHOLD_CENTS
    return {
        "transactionId": transaction.get("transactionId"),
        "accountId": transaction.get("accountId"),
        "amount": amount,
        "flagged": flagged,
        "reason": "Amount exceeds AML threshold" if flagged else "Passed AML check",
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> None:
    transactions = _parse_sqs_event(event)
    if not transactions:
        log_struct(logger, logger.level, "No valid transactions to process")
        return

    for tx in transactions:
        result = _run_aml_check(tx)
        log_struct(
            logger,
            logger.level,
            "AML check completed",
            **result,
        )
        if result["flagged"]:
            logger.warning("Flagged transaction requires manual review", extra=result)
