import json
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from shared.utils.logger import get_logger, log_struct

logger = get_logger(__name__)

FRAUD_SCORE_THRESHOLD = float(os.getenv("FRAUD_SCORE_THRESHOLD", "0.8"))


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


def _calculate_fraud_score(transaction: Dict[str, Any]) -> float:
    amount = transaction.get("amount", 0)
    score = 0.0
    if amount > 10_000_000:
        score += 0.4
    elif amount > 1_000_000:
        score += 0.2
    if transaction.get("type") == "transfer" and amount > 5_000_000:
        score += 0.3
    return min(score, 1.0)


def lambda_handler(event: Dict[str, Any], context: Any) -> None:
    transactions = _parse_sqs_event(event)
    if not transactions:
        log_struct(logger, logger.level, "No valid transactions to process")
        return

    for tx in transactions:
        score = _calculate_fraud_score(tx)
        is_suspicious = score >= FRAUD_SCORE_THRESHOLD
        log_struct(
            logger,
            logger.level,
            "Fraud detection completed",
            transactionId=tx.get("transactionId"),
            accountId=tx.get("accountId"),
            fraudScore=round(score, 4),
            suspicious=is_suspicious,
        )
        if is_suspicious:
            logger.warning(
                "Suspicious transaction flagged for review",
                extra={"transactionId": tx.get("transactionId"), "score": score},
            )
