import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
from domains.finance_orchestration.src.process_transaction.lambda_function import (
    _build_response,
    _validate_transaction,
    lambda_handler,
)


class TestValidateTransaction(unittest.TestCase):
    def test_valid_transaction(self):
        body = {
            "accountId": "acc-123",
            "amount": 5000,
            "currency": "USD",
            "type": "deposit",
        }
        _validate_transaction(body)

    def test_missing_fields(self):
        with self.assertRaises(ValueError):
            _validate_transaction({"amount": 100})

    def test_negative_amount(self):
        with self.assertRaises(ValueError):
            _validate_transaction(
                {"accountId": "a1", "amount": -10, "currency": "USD", "type": "payment"}
            )

    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            _validate_transaction(
                {"accountId": "a1", "amount": 100, "currency": "USD", "type": "invalid"}
            )


class TestBuildResponse(unittest.TestCase):
    def test_response_format(self):
        resp = _build_response(202, {"message": "ok"})
        self.assertEqual(resp["statusCode"], 202)
        self.assertIn("application/json", resp["headers"]["Content-Type"])

    def test_body_is_json(self):
        resp = _build_response(400, {"error": "bad request"})
        parsed = json.loads(resp["body"])
        self.assertEqual(parsed["error"], "bad request")


class TestLambdaHandler(unittest.TestCase):
    @patch(
        "domains.finance_orchestration.src.process_transaction.lambda_function.eventbridge"
    )
    def test_successful_processing(self, mock_eb: MagicMock):
        mock_eb.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "evt-1"}],
        }
        event = {
            "body": json.dumps(
                {
                    "accountId": "acc-1",
                    "amount": 2500,
                    "currency": "USD",
                    "type": "transfer",
                }
            )
        }
        resp = lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 202)
        body = json.loads(resp["body"])
        self.assertIn("transactionId", body)

    @patch(
        "domains.finance_orchestration.src.process_transaction.lambda_function.eventbridge"
    )
    def test_validation_error(self, mock_eb: MagicMock):
        event = {"body": json.dumps({"amount": -5})}
        resp = lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 400)

    @patch(
        "domains.finance_orchestration.src.process_transaction.lambda_function.eventbridge"
    )
    def test_eventbridge_failure(self, mock_eb: MagicMock):
        mock_eb.put_events.return_value = {
            "FailedEntryCount": 1,
            "Entries": [
                {"ErrorCode": "InternalFailure", "ErrorMessage": "something went wrong"}
            ],
        }
        event = {
            "body": json.dumps(
                {"accountId": "a1", "amount": 100, "currency": "USD", "type": "payment"}
            )
        }
        resp = lambda_handler(event, None)
        self.assertEqual(resp["statusCode"], 500)

    def test_missing_body(self):
        resp = lambda_handler({}, None)
        self.assertEqual(resp["statusCode"], 400)
        body = json.loads(resp["body"])
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()