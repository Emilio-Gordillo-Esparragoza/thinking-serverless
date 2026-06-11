import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
from shared.utils.logger import get_logger, log_struct

logger = get_logger(__name__)

AML_THRESHOLD_CENTS = int(os.getenv("AML_THRESHOLD_CENTS", "1000000"))
FRAUD_THRESHOLD_CENTS = int(os.getenv("FRAUD_THRESHOLD_CENTS", "5000000"))


def _validate(body: Dict[str, Any]) -> None:
    required = {"accountId", "amount", "currency", "type"}
    missing = required - set(body.keys())
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    if not isinstance(body.get("amount"), (int, float)) or body["amount"] <= 0:
        raise ValueError("amount must be a positive number")
    valid_types = {"deposit", "withdrawal", "transfer", "payment"}
    if body.get("type") not in valid_types:
        raise ValueError(f"type must be one of {valid_types}")


def _run_compliance(transaction_id: str, amount: int) -> Dict[str, Any]:
    flagged = amount > AML_THRESHOLD_CENTS
    if flagged:
        log_struct(
            logger,
            logger.level,
            "Compliance check flagged",
            transactionId=transaction_id,
            amount=amount,
        )
    return {
        "flagged": flagged,
        "reason": "AML threshold exceeded" if flagged else "passed",
    }


def _run_fraud_check(transaction_id: str, amount: int, tx_type: str) -> Dict[str, Any]:
    score = 0.0
    if amount > 10_000_000:
        score += 0.4
    elif amount > 1_000_000:
        score += 0.2
    if tx_type == "transfer" and amount > 5_000_000:
        score += 0.3
    score = min(score, 1.0)
    suspicious = score >= 0.8
    if suspicious:
        log_struct(
            logger,
            logger.level,
            "Fraud check flagged",
            transactionId=transaction_id,
            score=round(score, 4),
        )
    return {"suspicious": suspicious, "score": round(score, 4)}


def _update_ledger(
    transaction_id: str, account_id: str, amount: int, tx_type: str
) -> Dict[str, Any]:
    debit = {
        "entryId": f"{transaction_id}-debit",
        "accountId": account_id,
        "amount": amount,
    }
    credit = {
        "entryId": f"{transaction_id}-credit",
        "accountId": account_id,
        "amount": amount,
    }
    log_struct(
        logger,
        logger.level,
        "Ledger updated",
        transactionId=transaction_id,
        debitEntryId=debit["entryId"],
        creditEntryId=credit["entryId"],
    )
    return {"debit": debit, "credit": credit}


def _respond(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = event.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)

        _validate(body)

        transaction_id = f"tx-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        amount = body["amount"]
        account_id = body["accountId"]
        tx_type = body["type"]

        compliance = _run_compliance(transaction_id, amount)
        if compliance["flagged"]:
            return _respond(
                403,
                {
                    "error": "Transaction blocked by compliance",
                    "transactionId": transaction_id,
                },
            )

        fraud = _run_fraud_check(transaction_id, amount, tx_type)
        if fraud["suspicious"]:
            return _respond(
                403,
                {
                    "error": "Transaction flagged as suspicious",
                    "transactionId": transaction_id,
                },
            )

        ledger = _update_ledger(transaction_id, account_id, amount, tx_type)

        log_struct(
            logger,
            logger.level,
            "Transaction completed synchronously",
            transactionId=transaction_id,
            amount=amount,
            type=tx_type,
        )
        return _respond(
            200,
            {
                "message": "Transaction completed",
                "transactionId": transaction_id,
                "compliance": compliance,
                "fraudCheck": fraud,
                "ledger": ledger,
            },
        )

    except ValueError as ve:
        return _respond(400, {"error": str(ve)})
    except Exception as _:
        logger.critical("Unexpected error", exc_info=True)
        return _respond(500, {"error": "Internal server error"})
