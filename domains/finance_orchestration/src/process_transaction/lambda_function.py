import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from shared.utils.logger import get_logger, log_struct

logger = get_logger(__name__)
eventbridge = boto3.client("events")

EVENT_BUS_NAME = os.getenv("EVENT_BUS_NAME", "finance-events")
MAX_RETRIES = 3


def _validate_transaction(body: Dict[str, Any]) -> None:
    required = {"accountId", "amount", "currency", "type"}
    missing = required - set(body.keys())
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    if not isinstance(body.get("amount"), (int, float)) or body["amount"] <= 0:
        raise ValueError("amount must be a positive number")
    if body.get("currency") and not isinstance(body["currency"], str):
        raise ValueError("currency must be a string")
    valid_types = {"deposit", "withdrawal", "transfer", "payment"}
    if body.get("type") not in valid_types:
        raise ValueError(f"type must be one of {valid_types}")


def _build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }


def _put_event_with_retry(detail: Dict[str, Any]) -> None:
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = eventbridge.put_events(
                Entries=[
                    {
                        "EventBusName": EVENT_BUS_NAME,
                        "Source": "finance.orchestration",
                        "DetailType": "TransactionProcessed",
                        "Detail": json.dumps(detail, default=str),
                    }
                ]
            )
            failed_count = response.get("FailedEntryCount", 0)
            if failed_count > 0:
                entry = response["Entries"][0]
                raise RuntimeError(
                    f"PutEvents failed: {entry.get('ErrorCode')} - {entry.get('ErrorMessage')}"
                )
            return
        except Exception as exc:
            last_exception = exc
            log_struct(
                logger,
                logger.level,
                "PutEvents attempt failed",
                attempt=attempt,
                max_retries=MAX_RETRIES,
                error=str(exc),
            )
    raise RuntimeError(
        f"PutEvents failed after {MAX_RETRIES} retries"
    ) from last_exception


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = event.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)

        _validate_transaction(body)

        transaction_id = str(uuid.uuid4())
        detail = {
            "transactionId": transaction_id,
            "accountId": body["accountId"],
            "amount": body["amount"],
            "currency": body["currency"],
            "type": body["type"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": body.get("metadata", {}),
        }

        _put_event_with_retry(detail)

        log_struct(
            logger,
            logger.level,
            "Transaction processed and event published",
            transaction_id=transaction_id,
            account_id=body["accountId"],
            amount=body["amount"],
            currency=body["currency"],
        )

        return _build_response(
            202,
            {
                "message": "Transaction accepted for processing",
                "transactionId": transaction_id,
            },
        )

    except ValueError as ve:
        logger.warning("Validation error", exc_info=True)
        return _build_response(400, {"error": str(ve)})
    except RuntimeError as re:
        logger.error("Processing error", exc_info=True)
        return _build_response(500, {"error": str(re)})
    except Exception as _:
        logger.critical("Unexpected error", exc_info=True)
        return _build_response(500, {"error": "Internal server error"})
